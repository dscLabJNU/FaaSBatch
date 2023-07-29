# ======= NEED TO CONFIG =======
MASTER_IP="192.168.1.18"
DOCKER_0_IP = "172.17.0.1" # it serves to communicate with the host-side components from the docker container, and it should be 172.17.0.1
# ======= NEED TO CONFIG =======


COUCHDB_URL = f'http://openwhisk:openwhisk@{MASTER_IP}:5984/'
REDIS_HOST = DOCKER_0_IP
REDIS_PORT = 6379
REDIS_DB = 0
