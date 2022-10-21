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
            '5000/tcp': str(port)}, "labels": ['azure-cpu'], "privileged":True}
        if bind_cpus:
            bind_cpus_str = ','.join(list(map(lambda x: str(x), bind_cpus))) # Maps a list [0,1,3] to a str '0,1,3'
            run_params.update({"cpuset_cpus": bind_cpus_str})
        print(f"run_params: {run_params}")
        container = client.containers.run(image_name, **run_params)
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
    def send_batch_requests(self, data={}):
        r = requests.post(base_url.format(self.port, 'batch_run'), json=data)
        self.lasttime = time.time()
        return r.json()

    # initialize the container
    def init(self):
        r = requests.post(base_url.format(self.port, 'init'))
        self.lasttime = time.time()
        return r.status_code == 200

    # kill and remove the container
    def destroy(self):
        self.container.remove(force=True)
