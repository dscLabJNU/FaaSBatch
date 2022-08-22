sudo systemctl daemon-reload
sudo systemctl restart docker

docker rm -f $(docker ps -aq)

docker run -itd -p 6379:6379 --name redis redis
