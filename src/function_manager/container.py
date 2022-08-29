from typing import Dict, List
import requests
import docker
import time
import gevent
from docker.types import Mount

base_url = 'http://127.0.0.1:{}/{}'


class Container:
    # create a new container and return the wrapper
    @classmethod
    def create(cls, client, image_name, port, attr):
        container = client.containers.run(image_name,
                                          detach=True,
                                          ports={'5000/tcp': str(port)},
                                          labels=['workflow'])
        res = cls(container, port, attr)
        res.wait_start()
        return res

    # get the wrapper of an existed container
    # container_id is the container's docker id
    @classmethod
    def inherit(cls, client, container_id, port, attr):
        container = client.containers.get(container_id)
        return cls(container, port, attr)

    def __init__(self, container, port, attr):
        self.container = container
        self.port = port
        self.attr = attr
        self.lasttime = time.time()

    # wait for the container cold start
    def wait_start(self):
        while True:
            try:
                r = requests.get(base_url.format(self.port, 'status'))
                if r.status_code == 200:
                    break
            except Exception:
                pass
            gevent.sleep(0.005)

    # send a request to container and wait for result
    def send_request(self, data):
        r = requests.post(base_url.format(self.port, 'run'), json=data)
        self.lasttime = time.time()
        return r.json()

    def send_batch_requests(self, requests: List) -> Dict:
        """Batching requests to a single container

        Args:
            requests (list): The batching requests

        Returns:
            dict: Return the container and its corresponding batching requests
        """
        print(
            f"Batching {len(requests)} of requests to container {self.container.name}")
        for req in requests:
            res = self.send_request(data=req.data)
            req.result.set(res)
        return {"container": self, "requests": requests}

    # initialize the container
    def init(self, workflow_name, function_name):
        data = {'workflow': workflow_name, 'function': function_name}
        r = requests.post(base_url.format(self.port, 'init'), json=data)
        self.lasttime = time.time()
        return r.status_code == 200

    # kill and remove the container
    def destroy(self):
        self.container.remove(force=True)
