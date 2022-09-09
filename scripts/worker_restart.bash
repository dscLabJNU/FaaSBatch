docker rm -f $(docker ps -aq)

sudo systemctl daemon-reload
sudo systemctl restart docker

docker run -itd -p 6379:6379 --name redis redis
cd ../benchmark/generator/azure-bench/
python3 generate_trace.py 
python3 build_images.py
cd -