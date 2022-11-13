function execRemoteCMD() {
    # execRemoteCMD will execute the commands in the remote host through `ssh`
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

function fetch_csvs() {
    csv_prefix=$1
    strategy=$2
    azure_type=$3
    remote_host=$4
    log_path=$5
    path_to_save_csvs=$6

    csv_file_name=$(printf "${csv_prefix}" $strategy)
    transfered_csv=$(printf "${csv_prefix}" "${strategy}_${azure_type}")
    printf "Fetching [$csv_file_name] from [$remote_host] and transfer it to [$transfered_csv]\n"
    # 1. Go to the log path and check if there is a target csv file
    filter_log_cmd="cd $log_path; ls $csv_file_name"
    # 2. Execute a sepecific command if pass the $filter_log_cmd
    exec_command="$filter_log_cmd; scp -r $csv_file_name dev-03:$path_to_save_csvs"
    execRemoteCMD "${remote_host}" "${filter_log_cmd}" "${exec_command}"
    mv "$path_to_save_csvs/$csv_file_name" "$path_to_save_csvs/$transfered_csv"
}

latency_log_path=$(awk -F= '/latency_log_path/{print $2}' experiment.config)
resource_log_path=$(awk -F= '/resource_log_path/{print $2}' experiment.config)

azure_type=$1
case "$azure_type" in
"cpu" | "io")
    remote_hosts=${@:2}
    latency_csv_prefix="latency_amplification_%s%s.csv"
    utilization_csv_prefix="utilization_%s%s.csv"
    results_dir="/home/vagrant/batching-request/test/asplos/e2e_latency_and_colocation/results"
    strategies=(BaseBatching Kraken Batching SFS)

    path_to_save_csvs=$results_dir/$azure_type
    mkdir -p $path_to_save_csvs

    for remote_host in ${remote_hosts[@]}; do
        for strategy in ${strategies[@]}; do
            fetch_csvs $latency_csv_prefix $strategy $azure_type $remote_host $latency_log_path $path_to_save_csvs
            fetch_csvs $utilization_csv_prefix $strategy $azure_type $remote_host $resource_log_path $path_to_save_csvs
            echo
        done
        echo
    done
    ;;
*)
    printf "azure_type shoud be 'cpu' or 'io'\n"
    ;;
esac
