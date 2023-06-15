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
    def create(cls, client, image_name, port, attr, bind_cpus=None):
        run_params = {"detach": True, "ports": {
            '5000/tcp': str(port)}, "labels": ['workflow'], "privileged": True, "pid_mode": "host"}
        if bind_cpus:
            # Maps a list [0,1,3] to a str '0,1,3'
            bind_cpus_str = ','.join(list(map(lambda x: str(x), bind_cpus)))
            run_params.update({"cpuset_cpus": bind_cpus_str})
        print(f"run_params: {run_params}")
        start = time.time()
        container = client.containers.run(image_name, **run_params)
        res = cls(container, port, attr)
        res.wait_start()
        res.cold_start = (time.time() - start) * 1000  # Converts s to ms
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
        self.cold_start = None
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
            req.start_exec = time.time()
            req.data['container_name'] = self.container.name
            req.data['cold_start'] = self.cold_start
            print(f"executing req: {req.function_id}")

        d_list = list(map(lambda x: x.data, reqs))
        print(f"data list is: {d_list}")
        r = requests.post(base_url.format(self.port, 'batch_run'), json=d_list)
        print(f"Received {len(r.json())} of result of this batching")
        print(f"r.json() = {r.json()}")
        for req in reqs:
            if len(r.json()) == 0:
                # For some non-return functions
                req.result.set({})
                continue
            print(f"receiving req: {req.function_id}")
            function_id = req.function_id
            res = r.json()[function_id]
            req.result.set(res)
            req.end_exec = time.time()
            req.duration = (req.end_exec - req.start_exec) * 1000
            print(f"Result of request: {function_id} is {res}")
        self.lasttime = time.time()
        return {"container": self, "requests": reqs}

    # initialize the container
    def init(self, workflow_name, function_name):
        data = {'workflow': workflow_name, 'function': function_name}
        r = requests.post(base_url.format(self.port, 'init'), json=data)
        self.lasttime = time.time()
        return r.status_code == 200

    def set_cache_strategy(self, cache_strategy):
        """
        A cache scheduling strategy that manages the socket client instances inside container
        Only for evaluating the efficiency of io_optimize function.
        """
        if not cache_strategy:
            return
        data = {"cache_strategy": cache_strategy}
        r = requests.post(base_url.format(self.port, 'set_strategy'), json=data)
        return r.status_code == 200

    # kill and remove the container
    def destroy(self):
        self.container.remove(force=True)
