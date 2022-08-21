
function clean_monitor(){
    echo "Cleaning monitor processes in remote hosts..."
    kill_resource_cmd="ps -ef | grep -v grep |grep -E 'monitor_resources' | awk '{print \$2}'| xargs kill -9"
    ssh dev-01 $kill_resource_cmd
    ssh dev-02 $kill_resource_cmd
}

function clean_proxy(){
    echo "Cleaning proxy processes in remote hosts..."
    kill_proxy_cmd="ps -ef | grep -v grep |grep -E 'python3 proxy.py' | awk '{print \$2}'| xargs kill -9"
    ssh dev-01 $kill_proxy_cmd
    ssh dev-02 $kill_proxy_cmd
}

function run_monitor(){
    strategy=$1
    run_monitor_cmd="cd ~/openwhisk-resource-monitor; nohup ./monitor_resources.sh > utilization_$strategy.csv &"
    ssh dev-01 $run_monitor_cmd
    ssh dev-02 $run_monitor_cmd
    echo "Run remote monitor processes done... now need to wait for 40 s"
}

function usage() {
    echo -e "Usage: $0 [Batching, Fifer, FaaSFlow]"
}


if [[ $# -lt 1 ]]; then
    usage
else
    echo "Now running benchmark with strategy=$1"
    strategy=$1

    clean_monitor

    # 1. Run monitor before benchmarking
    run_monitor $strategy
    # sleep 40
    echo "Now running benchmark..."

    # 2. Run benmark
    python3 run.py --datamode=opmized --mode=corun

    echo "Benchmarking process done, now need to wait for 40 s"
    # sleep 40

    clean_monitor
    clean_proxy
    echo "Clean done"
fi
