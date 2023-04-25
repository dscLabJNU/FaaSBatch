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
    SLO_quantails=$2
    remote_hosts=${@:3}

    ./run.sh Kraken ${azure_type}_native ${SLO_quantails} ${remote_hosts}
    bash fetch_results.sh ${azure_type} ${SLO_quantails} "Kraken" ${remote_hosts[@]}

}

function runSensitive() {
    azure_type=$1
    remote_hosts=${@:2}

    SLO_quantails=(0.4 0.45 0.5 0.55 0.6 0.65 0.7 0.75 0.8 0.85 0.9 0.95 0.98)
    for SLO_quantail in ${SLO_quantails[@]}; do
        runStrategy ${azure_type} ${SLO_quantail} ${remote_hosts[@]}
    done
}
if [[ $# -lt 1 ]]; then
    usage
else
    azure_type=$1
    # remote_hosts=(dev-01 dev-02 dev-04)
    remote_hosts=(dev-01)
    echo -e "[SLO_quantails sensitivity] \nOnly Running Kraken strategy with AZURE_TYPE is [$azure_type] and REMOTE_HOSTS are [${remote_hosts[@]}]"
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
