CURRENT_DIR=$(cd "$(dirname "$0")"; pwd)

# install docker
sudo apt-get update
sudo apt-get install python3-pip -y
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

# install redis
docker pull redis
docker run -itd -p 6379:6379 --name redis redis
cd $CURRENT_DIR../benchmark/generator/azure-bench
python3 generate_trace.py
python3 build_images.py