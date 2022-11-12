trap 'onCtrlC' INT

function onCtrlC() {
    echo 'capture Ctrl + C'
    ./stop_all.sh
    exit
}

./run.sh BaseBatching

./run.sh Kraken

./run.sh Batching

./run.sh SFS
