trap 'onCtrlC' INT

function onCtrlC() {
    echo 'capture Ctrl + C'
    clean_monitor
    clean_proxy_gateway
    exit
}

function execRemoteCMD() {
    remote_host=$1
    ps_command=$2
    exec_command=$3

    # Resolve the IP address of the remote_host
    remote_ip=$(getent hosts $remote_host | awk '{ print $1 }')

    # Check if the IP address of the remote_host is local
    local_ips=$(hostname -I)
    if [[ $local_ips == *"$remote_ip"* ]]; then
        execLocalCMD "$ps_command" "$exec_command"
    else
        filter_result=$(ssh $remote_host $ps_command)
        if [ -n "$filter_result" ]; then
            echo "Executing: ssh $remote_host '$exec_command'"
            ssh $remote_host "$exec_command"
        else
            echo "Nothing to exec of cmd: [$ps_command] in host [$remote_host]"
        fi
    fi
}



function execLocalCMD() {
    ps_command=$1
    exec_command=$2

    # Save current working directory
    old_pwd=$(pwd)

    filter_result=$(eval $ps_command)
    if [ -n "$filter_result" ]; then
        echo "Executing: '$exec_command' in local"
        eval "$exec_command"
    else
        echo "Nothing to exec of cmd: [$ps_command]"
    fi

    # Restore working directory
    cd "$old_pwd"
}

function clean_monitor() {
    remote_hosts=$@
    echo -e "1. Cleaning monitor processes in remote hosts..."
    ps_command="ps -ef | grep -v grep |grep -E 'monitor_resources'"
    exec_command="$ps_command | awk '{print \$2}'| xargs kill -9"
    for remote_host in ${remote_hosts[@]}; do
        execRemoteCMD "$remote_host" "${ps_command}" "${exec_command}"
    done
}

function clean_proxy_gateway() {
    remote_hosts=$@
    echo -e "\n2. Cleaning proxy processes in remote hosts..."
    ps_proxy_cmd="ps -ef | grep -v grep |grep -E 'python3 proxy.py' | awk '{print \$2}'"
    exec_command="sudo kill -9 \$($ps_proxy_cmd)"
    for remote_host in ${remote_hosts[@]}; do
        execRemoteCMD "${remote_host}" "${ps_proxy_cmd}" "${exec_command}"
    done

    ps_gateway_cmd="ps -ef | grep -v grep |grep -E 'python3 gateway.py' | awk '{print \$2}'"
    exec_command="sudo kill -9 \$($ps_gateway_cmd)"
    execRemoteCMD "dev-03" "${ps_gateway_cmd}" "${exec_command}"
}

function clean_previous_containers() {
    remote_hosts=$@
    echo -e "\n3. Cleaning containers in remote hosts..."
    ps_command="docker ps -aq --filter label=workflow"
    exec_command="docker rm -f \$($ps_command) >/dev/null 2>&1"
    for remote_host in ${remote_hosts[@]}; do
        execRemoteCMD "${remote_host}" "${ps_command}" "${exec_command}"
    done
}

function rm_utilization_log() {
    resource_log_path=$(awk -F= '/resource_log_path/{print $2}' experiment.config)
    strategy=$1
    remote_hosts=${@:2}
    echo -e "\n4. Removing utilization log of strategy $strategy"
    rm_utilization_log_cmd="rm -rf $resource_log_path/utilization_$strategy.csv"
    for remote_host in ${remote_hosts[@]}; do
        ssh $remote_host $rm_utilization_log_cmd
    done

}

function run_proxy_gateway() {
    echo -e "\n5. Staring proxy (and gateway) processes in remote hosts"

    strategy=$1
    dispatch_interval=$2
    remote_hosts=${@:3}
    workflow_path=$(awk -F= '/workflow_path/{print $2}' experiment.config)

    cd_cmd="cd $workflow_path"
    export_cmd="export strategy=$strategy; export dispatch_interval=$dispatch_interval"

    ps_proxy_cmd="${cd_cmd}; ${export_cmd}; ls run-proxy.sh;"
    launch_proxy_cmd="${ps_proxy_cmd} nohup bash run-proxy.sh"

    ps_gateway_cmd="${cd_cmd}; ${export_cmd}; ls run-gateway.sh;"
    launch_gateway_cmd="${ps_gateway_cmd} nohup bash run-gateway.sh"

    dev03_ip=$(awk -F= '/dev-03_ip/{print $2}' experiment.config)

    for remote_host in ${remote_hosts[@]}; do
        ip=$(awk -F= '/'$remote_host'_ip/{print $2}' experiment.config)
        execRemoteCMD "${remote_host}" "${ps_proxy_cmd}" "${launch_proxy_cmd} "$ip" > proxy_$strategy.log &"
    done
    
    execRemoteCMD "dev-03" "${ps_proxy_cmd}" "${launch_gateway_cmd} ${dev03_ip} > gateway_$strategy.log &"

}

function run_monitor() {
    resource_log_path=$(awk -F= '/resource_log_path/{print $2}' experiment.config)
    strategy=$1
    remote_hosts=${@:2}
    cd_cmd="cd $resource_log_path"
    ps_command="${cd_cmd}; ls monitor_resources.sh "
    exec_command="${cd_cmd}; nohup ./monitor_resources.sh > utilization_$strategy.csv &"
    for remote_host in ${remote_hosts[@]}; do
        execRemoteCMD "${remote_host}" "${ps_command}" "${exec_command}"
    done
    echo "Run remote monitor processes done..."
}


function usage() {
    echo -e "Usage: $0 [FaaSBatch, BaseBatching, Kraken, SFS] [cpu, io]"
}

if [[ $# -lt 2 ]]; then
    usage
else
    # init the experimental setup
    bash init_exper_config.sh

    strategy=$1
    azure_type=$2
    dispatch_interval=$3
    remote_hosts=${@:4}

    clean_monitor $remote_hosts
    clean_proxy_gateway $remote_hosts
    clean_previous_containers $remote_hosts

    rm_utilization_log $strategy $remote_hosts
    run_proxy_gateway $strategy $dispatch_interval $remote_hosts
    echo "Wait 5 seconds for launching proxy and gateway"
    sleep 5

    # 1. Run monitor before benchmarking
    run_monitor $strategy $remote_hosts

    echo "Now running benchmark..."
    case "$strategy" in
    "FaaSBatch")
        python3 -u run.py --mode azure_bench --azure_type ${azure_type}
        ;;
    "BaseBatching")
        python3 -u run.py --mode azure_bench --azure_type ${azure_type}
        ;;
    "SFS")
        python3 -u run.py --mode azure_bench --azure_type ${azure_type}
        ;;
    "Kraken")
        python3 -u run.py --mode azure_bench --azure_type ${azure_type}
        ;;
    *)
        usage
        ;;
    esac
    clean_monitor $remote_hosts
fi
