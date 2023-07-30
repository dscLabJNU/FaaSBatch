import sys
import socket
import fcntl
import struct
sys.path.append('../../config')
import config

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                            struct.pack('256s', ifname[:15].encode('utf-8')))[20:24])

MASTER_IP=config.MASTER_IP
DOCKER_0_IP = get_ip_address('docker0') # it serves to communicate with the host-side components from the docker container, and it should be 172.17.0.1
COUCHDB_URL = f'http://openwhisk:openwhisk@{MASTER_IP}:5984/'
REDIS_HOST = DOCKER_0_IP
REDIS_PORT = 6379
REDIS_DB = 0
