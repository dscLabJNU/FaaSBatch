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
    filter_result=$(ssh $remote_host $ps_command)
    if [ -n "$filter_result" ]; then
        echo "Executing: ssh $remote_host '$exec_command'"
        ssh $remote_host "$exec_command"
    else
        echo "Nothing to exec of cmd: [$ps_command] in host [$remote_host]"
    fi
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
    strategy=$1
    remote_hosts=${@:2}
    echo -e "\n4. Removing utilization log of strategy $strategy"
    rm_utilization_log_cmd="rm -rf /home/vagrant/openwhisk-resource-monitor/utilization_$strategy.csv"
    for remote_host in ${remote_hosts[@]}; do
        ssh $remote_host $rm_utilization_log_cmd
    done

}

function run_proxy_gateway() {
    echo -e "\n5. Staring proxy (and gateway) processes in remote hosts"

    strategy=$1
    dispatch_interval=$2
    remote_hosts=${@:3}
    cd_cmd="cd /home/vagrant/batching-request/src/workflow_manager"
    export_cmd="export strategy=$strategy; export dispatch_interval=$dispatch_interval"

    ps_proxy_cmd="${cd_cmd}; ${export_cmd}; ls run-proxy.sh;"
    launch_proxy_cmd="${ps_proxy_cmd} nohup bash run-proxy.sh"

    ps_gateway_cmd="${cd_cmd}; ${export_cmd}; ls run-gateway.sh;"
    launch_gateway_cmd="${ps_gateway_cmd} nohup bash run-gateway.sh"

    for remote_host in ${remote_hosts[@]}; do
        ip=$(awk -F= '/'$remote_host'_ip/{print $2}' experiment.config)
        execRemoteCMD "${remote_host}" "${ps_proxy_cmd}" "${launch_proxy_cmd} "$ip" > proxy_$strategy.log &"
    done

    execRemoteCMD "dev-03" "${ps_proxy_cmd}" "${launch_gateway_cmd} 10.0.0.103 > gateway_$strategy.log &"

}

function run_monitor() {
    strategy=$1
    remote_hosts=${@:2}
    run_monitor_cmd="cd ~/openwhisk-resource-monitor; nohup ./monitor_resources.sh > utilization_$strategy.csv &"
    for remote_host in ${remote_hosts[@]}; do
        ssh $remote_host $run_monitor_cmd
    done
    echo "Run remote monitor processes done... now need to wait for 40 s"
}

function usage() {
    echo -e "Usage: $0 [FaaSBatch] [cpu, io]"
}

if [[ $# -lt 2 ]]; then
    usage
else
    strategy=$1
    azure_type=$2
    dispatch_interval=$3
    cache_strategy=$4
    cache_size=$5
    remote_hosts=${@:6}

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
        python3 -u run.py --mode azure_bench --azure_type ${azure_type} --cache_strategy ${cache_strategy} --cache_size ${cache_size}
    ;;
    esac
    clean_monitor $remote_hosts
fi
