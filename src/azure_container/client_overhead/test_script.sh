#!/bin/bash  

# kill proxy
kill $(ps -ef | grep proxy.py | grep -v grep | awk '{print $2}')
mkdir -p logs
touch ./logs/s3_resource.csv
echo "time(ms),memory(MB),concurrency" > ./logs/s3_resource.csv
for i in $(seq 1 5)
do
    for concur in $(seq 1 10)
    do   
    nohup python proxy.py &
    sleep 0.5
    concurrency=$concur
    echo concurrency=$concurrency


    python post_requests.py -c $concurrency
    # kill proxy
    kill $(ps -ef | grep proxy.py | grep -v grep | awk '{print $2}')
    done   
done
