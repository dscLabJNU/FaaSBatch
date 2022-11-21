trap 'onCtrlC' INT

function onCtrlC() {
    echo 'capture Ctrl + C'
    ./stop_all.sh
    exit
}

function usage() {
    echo -e "Usage: $0 [cpu, io, all]"
}

function runStrategy() {
    azure_type=$1
    dispatch_interval=$2
    remote_hosts=${@:3}

    ./run.sh BaseBatching ${azure_type}_native ${dispatch_interval} ${remote_hosts}
    bash fetch_results.sh ${azure_type} ${dispatch_interval} "BaseBatching" ${remote_hosts[@]}

    ./run.sh Kraken ${azure_type}_native ${dispatch_interval} ${remote_hosts}
    bash fetch_results.sh ${azure_type} ${dispatch_interval} "Kraken" ${remote_hosts[@]}

    ./run.sh Batching ${azure_type}_optimize ${dispatch_interval} ${remote_hosts}
    bash fetch_results.sh ${azure_type} ${dispatch_interval} "Batching" ${remote_hosts[@]}

    ./run.sh SFS ${azure_type}_native ${dispatch_interval} ${remote_hosts}
    bash fetch_results.sh ${azure_type} ${dispatch_interval} "SFS" ${remote_hosts[@]}
}

function runSensitive() {
    azure_type=$1
    remote_hosts=${@:2}

    dispatch_intervals=(0.01 0.05 0.1 0.15 0.2 0.3 0.4 0.5)
    for dispatch_interval in ${dispatch_intervals[@]}; do
        runStrategy ${azure_type} ${dispatch_interval} ${remote_hosts[@]}
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

    case "$azure_type" in
    "cpu" | "io")
        runSensitive $azure_type ${remote_hosts[@]}
        ;;
    "all")
        runSensitive io ${remote_hosts[@]}
        runSensitive cpu ${remote_hosts[@]}
        ;;
    esac
fi
