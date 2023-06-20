trap 'onCtrlC' INT

function onCtrlC() {
    echo 'capture Ctrl + C'
    ./stop_all.sh
    exit
}

function usage() {
    echo -e "Usage: $0 [io]"
}

function runStrategy() {
    azure_type=$1
    dispatch_interval=$2
    cache_strategy=$3
    remote_hosts=${@:4}
    ./run.sh FaaSBatch ${azure_type}_optimize ${dispatch_interval} ${cache_strategy} ${remote_hosts}
    bash fetch_results.sh ${azure_type} ${dispatch_interval} "FaaSBatch" ${cache_strategy} ${remote_hosts[@]}
}

function run() {
    azure_type=$1
    remote_hosts=${@:2}

    # dispatch_intervals=(0.01 0.05 0.1 0.15 0.2 0.3 0.4 0.5)
    dispatch_interval=0.2
    # cache_strategies=("LFU" "MyCache" "GDSF" "LRU")
    # cache_strategies=("MyCache" "LRU")
    cache_strategies=("MyCache")

    for cache_strategy in ${cache_strategies[@]}; do
        runStrategy ${azure_type} ${dispatch_interval} ${cache_strategy} ${remote_hosts[@]}
    done
}
if [[ $# -lt 1 ]]; then
    usage
else
    azure_type=$1
    # remote_hosts=(dev-01 dev-02 dev-04)
    remote_hosts=(dev-01)
    echo -e "[Dispatch_interval sensitivity] \nRunning all strategy with AZURE_TYPE is [$azure_type] and REMOTE_HOSTS are [${remote_hosts[@]}]"
    read -p "Press any key to confirm, or ctrl-C to stop."

    case "$azure_type" in "io")
        run $azure_type ${remote_hosts[@]}
        ;;
    esac
fi
