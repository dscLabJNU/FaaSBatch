CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)

docker rm -f $(docker ps -aq)

sudo systemctl daemon-reload
sudo systemctl restart docker

docker run -itd -p 6379:6379 --name redis redis
cd $CURRENT_DIR/../benchmark/generator/azure-bench/
python3 generate_trace.py 
python3 build_images.py