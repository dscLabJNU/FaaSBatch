trap 'onCtrlC' INT

function onCtrlC() {
    echo 'capture Ctrl + C'
    ./stop_all.sh
    exit
}

function usage() {
    echo -e "Usage: $0 [cpu, io, all]"
}

function runStrategy(){
    azure_type=$1
    remote_hosts=${@:2}
    ./run.sh BaseBatching ${azure_type}_native $remote_hosts
    ./run.sh Kraken ${azure_type}_native $remote_hosts
    ./run.sh Batching ${azure_type}_optimize $remote_hosts
    ./run.sh SFS ${azure_type}_native $remote_hosts
}

if [[ $# -lt 1 ]]; then
    usage
else
    azure_type=$1
    # remote_hosts=(dev-01 dev-02 dev-04)
    remote_hosts=(dev-01)
    echo -e "Running all strategy with AZURE_TYPE is [$azure_type] and REMOTE_HOSTS are [${remote_hosts[@]}]"
    read -p "Press any key to confirm, or ctrl-C to stop."

    case "$azure_type" in
    "cpu" | "io")
        runStrategy $azure_type ${remote_hosts[@]}
        bash fetch_results.sh $azure_type ${remote_hosts[@]}
        ;;
    "all")
        runStrategy io ${remote_hosts[@]}
        bash fetch_results.sh io ${remote_hosts[@]}
        
        runStrategy cpu ${remote_hosts[@]}
        bash fetch_results.sh cpu ${remote_hosts[@]}
        ;;
    esac
fi
