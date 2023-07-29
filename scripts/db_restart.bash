CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
sudo systemctl daemon-reload
sudo systemctl restart docker


docker rm -f $(docker ps -aq)

docker run -itd -p 5984:5984 -e COUCHDB_USER=openwhisk -e COUCHDB_PASSWORD=openwhisk --name couchdb couchdb
cd $CURRENT_DIR
python3 couchdb_starter.py

docker run -itd -p 6379:6379 --name redis redis
cd $CURRENT_DIR/../benchmark/generator/azure-bench/
python3 generate_trace.py 

cd $CURRENT_DIR/../src/grouping
python3 grouping.py azure_bench_all