import socket
import json


data = {"pid": "1234", "id": "43"}
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
send_data = json.dumps(data).encode("utf-8")
udp_socket.sendto(bytes(send_data), ("127.0.0.1", 4009))
udp_socket.close()
