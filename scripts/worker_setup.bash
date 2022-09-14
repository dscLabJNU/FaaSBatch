# install docker
apt-get update
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
# install python packages
pip3 install -r requirements.txt
# install redis
docker pull redis
docker run -itd -p 6379:6379 --name redis redis
# build docker images
docker build --no-cache -t workflow_base ../src/container
python3 ../benchmark/generator/translator.py
../benchmark/wordcount/create_image.sh
../benchmark/fileprocessing/create_image.sh
../benchmark/illgal_recognizer/create_image.sh
../benchmark/video/create_image.sh
cd ../benchmark/generator/azure-bench
python3 generate_trace.py
python3 build_images.py
cd -