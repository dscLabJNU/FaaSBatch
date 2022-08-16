function usage() {
    echo -e "Usage: $0 [host-ip]"
}

function check_ip(){
    IP_ADDR=$1

    #获取本机IP地址列表
    machine_ips=$(ip addr | grep 'inet' | grep -v 'inet6\|127.0.0.1' | grep -v grep | awk -F '/' '{print $1}' | awk '{print $2}')
    # echo "current machine ips: ${machine_ips}"

    #输入的IP与本机IP进行校验
    ip_check=false
    for machine_ip in ${machine_ips}; do
    if [[ "X${machine_ip}" == "X${IP_ADDR}" ]]; then
        ip_check=true
    fi
    done

    if [[ ${ip_check} != true ]]; then
    echo "your input ip: ${IP_ADDR} is not the current IP address of this machine!"
    exit 1
    fi 
}

if [[ $# -lt 1 ]]; then
    usage
else
    check_ip $1
python3 proxy.py $1 8000
fi