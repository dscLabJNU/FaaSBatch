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

    def send_batch_requests(self, reqs: List, executing_rqs: List) -> Dict:
        """Batching requests to a single container

        Args:
            requests (list): The batching requests

        Returns:
            dict: Return the container and its corresponding batching requests
        """
        print(
            f"Batching {len(reqs)} of requests to container {self.container.name}")
        for req in reqs:
            executing_rqs.append(req)
            req.start_ts = time.time()
        #     res = self.send_request(data=req.data)
        #     req.end_ts = time.time()
        #     req.result.set(res)
        #     req.duration = (req.end_ts - req.start_ts) * 1000
        
        d_list = list(map(lambda x: x.data, reqs))
        r = requests.post(base_url.format(self.port, 'batch_run'), json=d_list)
        print(f"Received {len(r.json())} of result of this batching")
        for req in reqs:
            request_id = req.request_id
            res = r.json()[request_id]
            req.result.set(res)
            req.end_ts = time.time()
            req.duration = (req.end_ts - req.start_ts) * 1000
            print(f"Result of request: {request_id} is {res}")
        self.lasttime = time.time()
        return {"container": self, "requests": reqs}

    # initialize the container
    def init(self, workflow_name, function_name):
        data = {'workflow': workflow_name, 'function': function_name}
        r = requests.post(base_url.format(self.port, 'init'), json=data)
        self.lasttime = time.time()
        return r.status_code == 200

    # kill and remove the container
    def destroy(self):
        self.container.remove(force=True)
