function clean_proxy_gateway() {
    echo "Cleaning proxy processes in remote hosts..."
    ps_proxy_cmd="ps -ef | grep -v grep |grep -E 'python3 proxy.py' | awk '{print \$2}'"
    exec_command="sudo kill -9 \$($ps_proxy_cmd)"

    execRemoteCMD "dev-01" "${ps_proxy_cmd}" "${exec_command}"
    execRemoteCMD "dev-02" "${ps_proxy_cmd}" "${exec_command}"
    execRemoteCMD "dev-04" "${ps_proxy_cmd}" "${exec_command}"

    ps_gateway_cmd="ps -ef | grep -v grep |grep -E 'python3 gateway.py' | awk '{print \$2}'"
    exec_command="sudo kill -9 \$($ps_gateway_cmd)"
    execRemoteCMD "dev-03" "${ps_gateway_cmd}" "${exec_command}"
}

function execRemoteCMD() {
    remote_host=$1
    ps_command=$2
    exec_command=$3

    filter_result=$(ssh $remote_host $ps_command)
    if [ -n "$filter_result" ]; then
        echo "Executing: ssh $remote_host $exec_command"
        ssh $remote_host $exec_command
    else
        echo "Nothing to exec of cmd: [$ps_command] in host [$remote_host]"
    fi
}

function clean_monitor() {
    echo "Cleaning monitor processes in remote hosts..."
    ps_command="ps -ef | grep -v grep |grep -E 'monitor_resources'"
    exec_command="$ps_command | awk '{print \$2}'| xargs kill -9"

    execRemoteCMD "dev-01" "${ps_command}" "${exec_command}"
    execRemoteCMD "dev-02" "${ps_command}" "${exec_command}"
    execRemoteCMD "dev-04" "${ps_command}" "${exec_command}"
}

clean_monitor
clean_proxy_gateway
