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
        echo "Executing: ssh '$remote_host $exec_command'"
        ssh $remote_host $exec_command
    else
        echo "Nothing to exec of cmd: [$ps_command] in host [$remote_host]"
    fi
}

function clean_monitor() {
    echo -e "1. Cleaning monitor processes in remote hosts..."
    ps_command="ps -ef | grep -v grep |grep -E 'monitor_resources'"
    exec_command="$ps_command | awk '{print \$2}'| xargs kill -9"

    execRemoteCMD "dev-01" "${ps_command}" "${exec_command}"
    execRemoteCMD "dev-02" "${ps_command}" "${exec_command}"
    execRemoteCMD "dev-04" "${ps_command}" "${exec_command}"
}

function clean_proxy_gateway() {
    echo -e "\n2. Cleaning proxy processes in remote hosts..."
    ps_proxy_cmd="ps -ef | grep -v grep |grep -E 'python3 proxy.py' | awk '{print \$2}'"
    exec_command="sudo kill -9 \$($ps_proxy_cmd)"

    execRemoteCMD "dev-01" "${ps_proxy_cmd}" "${exec_command}"
    execRemoteCMD "dev-02" "${ps_proxy_cmd}" "${exec_command}"
    execRemoteCMD "dev-04" "${ps_proxy_cmd}" "${exec_command}"

    ps_gateway_cmd="ps -ef | grep -v grep |grep -E 'python3 gateway.py' | awk '{print \$2}'"
    exec_command="sudo kill -9 \$($ps_gateway_cmd)"
    execRemoteCMD "dev-03" "${ps_gateway_cmd}" "${exec_command}"
}

function clean_previous_containers() {
    echo -e "\n3. Cleaning containers in remote hosts..."
    ps_command="docker ps -aq --filter label=workflow"
    exec_command="docker rm -f \$($ps_command) >/dev/null 2>&1"
    execRemoteCMD "dev-01" "${ps_command}" "${exec_command}"
    execRemoteCMD "dev-02" "${ps_command}" "${exec_command}"
    execRemoteCMD "dev-04" "${ps_command}" "${exec_command}"
}

function rm_utilization_log() {
    strategy=$1
    echo -e "\n4. Removing utilization log of strategy $strategy"
    rm_utilization_log_cmd="rm -rf /home/vagrant/openwhisk-resource-monitor/utilization_$strategy.csv"
    ssh dev-01 $rm_utilization_log_cmd
    ssh dev-02 $rm_utilization_log_cmd
    ssh dev-04 $rm_utilization_log_cmd

}

function run_proxy_gateway() {
    echo -e "\n5. Staring proxy (and gateway) processes in remote hosts"

    strategy=$1
    cd_cmd="cd /home/vagrant/batching-request/src/workflow_manager"
    export_cmd="export strategy=$strategy"

    ps_proxy_cmd="${cd_cmd}; ${export_cmd}; ls run-proxy.sh;"
    launch_proxy_cmd="${ps_proxy_cmd} nohup bash run-proxy.sh"

    ps_gateway_cmd="${cd_cmd}; ${export_cmd}; ls run-gateway.sh;"
    launch_gateway_cmd="${ps_gateway_cmd} nohup bash run-gateway.sh"

    execRemoteCMD "dev-01" "${ps_proxy_cmd}" "${launch_proxy_cmd} 10.0.0.101 > proxy_$strategy.log &"
    execRemoteCMD "dev-02" "${ps_proxy_cmd}" "${launch_proxy_cmd} 10.0.0.102 > proxy_$strategy.log &"
    execRemoteCMD "dev-03" "${ps_proxy_cmd}" "${launch_gateway_cmd} 10.0.0.103 > gateway_$strategy.log &"
    execRemoteCMD "dev-04" "${ps_proxy_cmd}" "${launch_proxy_cmd} 10.0.0.104  > proxy_$strategy.log &"

}

function run_monitor() {
    strategy=$1
    run_monitor_cmd="cd ~/openwhisk-resource-monitor; nohup ./monitor_resources.sh > utilization_$strategy.csv &"
    ssh dev-01 $run_monitor_cmd
    ssh dev-02 $run_monitor_cmd
    ssh dev-04 $run_monitor_cmd
    echo "Run remote monitor processes done... now need to wait for 40 s"
}

function usage() {
    echo -e "Usage: $0 [Batching, BaseBatching, Kraken, SFS]"
}

if [[ $# -lt 1 ]]; then
    usage
else
    strategy=$1
    clean_monitor
    clean_proxy_gateway
    clean_previous_containers

    rm_utilization_log $strategy
    run_proxy_gateway $strategy
    echo "Wait 20 seconds for launching proxy and gateway"
    sleep 20

    # 1. Run monitor before benchmarking
    run_monitor $strategy

    echo "Now running benchmark..."
    case "$strategy" in
    "Batching")
        python3 run.py --mode azure_bench --azure_type cpu_optimize
        ;;
    "BaseBatching")
        python3 run.py --mode azure_bench --azure_type cpu_native
        ;;
    "SFS")
        python3 run.py --mode azure_bench --azure_type cpu_native
        ;;
    "Kraken")
        python3 run.py --mode azure_bench --azure_type cpu_native
        ;;
    *)
        usage
        ;;
    esac
    clean_monitor
fi
