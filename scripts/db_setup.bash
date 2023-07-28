CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)
# install docker
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo chown "$USER":"$USER" /home/"$USER"/.docker -R
sudo chmod g+rwx "/home/$USER/.docker" -R
sudo apt-get install wondershaper
# install and initialize couchdb
docker pull couchdb
docker run -itd -p 5984:5984 -e COUCHDB_USER=openwhisk -e COUCHDB_PASSWORD=openwhisk --name couchdb couchdb
apt-get install python3-pip -y
cd $CURRENT_DIR
python3 couchdb_starter.py
# install redis
docker pull redis
docker run -itd -p 6379:6379 --name redis redis
# run grouping for all benchmarks
cd $CURRENT_DIR/../src/grouping
python3 grouping.py azure_bench_all