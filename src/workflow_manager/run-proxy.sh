function usage() {
    echo -e "Usage: $0 [host-ip]"
}

function kill_SFS(){
    echo "Killing sfs-scheduler..."
    kill_cmd=$(ps -ef | grep -E "./sfs-scheduler" | grep -v grep | awk '{print $2}')
    kill $kill_cmd
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
    ip=$1
    check_ip $ip
if [[ ${strategy} == "SFS" ]]; then
    kill_SFS
    echo "launching SFS scheduler..."
    source ../../config/constants.config
    cd $SFSPath
    nohup bash run.sh &> SFS.out&
    cd -
fi
python3 proxy.py $ip 8000
fi