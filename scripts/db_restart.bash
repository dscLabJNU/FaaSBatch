sudo systemctl daemon-reload
sudo systemctl restart docker


docker rm -f $(docker ps -aq)

docker run -itd -p 5984:5984 -e COUCHDB_USER=openwhisk -e COUCHDB_PASSWORD=openwhisk --name couchdb couchdb
cd /home/vagrant/batching-request/scripts
python3 couchdb_starter.py

docker run -itd -p 6379:6379 --name redis redis
cd -

cd /home/vagrant/batching-request/src/grouping

python3 grouping.py azure_bench_all video illgal_recognizer fileprocessing wordcount cycles epigenomics genome soykb


cd -