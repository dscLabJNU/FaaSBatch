import logging
import queue
import time
import math
from deprecated import deprecated
from gevent import event
from gevent.lock import BoundedSemaphore
from container import Container
from function_info import FunctionInfo
from function import Function
import numpy as np

"""
Data structure for request info
"""


class RequestInfo:
    def __init__(self, function, request_id, data):
        self.function = function
        self.request_id = request_id
        self.data = data
        self.result = event.AsyncResult()
        self.arrival = time.time()


"""
Each function group represents a typical function, a group contains number of function instances
"""


class FunctionGroup():
    def __init__(self, name, functions, docker_client, port_controller) -> None:
        self.name = name
        self.functions = functions

        self.client = docker_client
        self.port_controller = port_controller

        self.num_processing = 0
        self.rq = []

        # container pool
        # the number of containers in execution, not in container pool
        self.num_exec = 0
        # self.num_exec = {
        # function.info.function_name: 0 for function in functions}

        # 创建完毕并执行完请求的容器，用于接收后续请求
        self.container_pool = []
        # 已经创建但是未执行过请求的容器，即创建完毕但是没有放在container_pool的容器，用于将并发请求按顺序排队
        self.candidate_containers = []

        self.b = BoundedSemaphore()
        

    # put the request into request queue
    def send_request(self, function, request_id, runtime, input, output, to, keys):
        data = {'request_id': request_id, 'runtime': runtime,
                'input': input, 'output': output, 'to': to, 'keys': keys}
        req = RequestInfo(function, request_id, data)
        self.rq.append(req)

        # res = function.send_request(request_id, runtime, input, output, to, keys)

        res = req.result.get()
        return res

    # receive a request from upper layer
    def dispatch_request(self, container=None):
        # no request to dispatch
        if len(self.rq) - self.num_processing == 0:
            return
        if len(self.rq) == 0:
            return 0
        self.num_processing += 1
        function = self.rq[0].function

        function_names = [rq.function.info.function_name for rq in self.rq]
        print(
            f"{self.name} has {len(function_names)} of function waiting to shedule: {function_names}")

        # 1. try to get a workable container from pool
        # container = function.self_container()
        container = self.self_container(function)

        # create a new container
        while container is None:
            # container = function.create_container()
            container = self.create_container(function)

        # the number of exec container hits limit
        if container is None:
            self.num_processing -= 1
            return

        while self.rq:
            self.num_processing -= 1
            print(
                f"The length of rq in this {self.name} group is {len(self.rq)}")

            req = self.rq.pop(0)
            print(
                f"Ready for batching request {req.function.info.function_name} in container {container.img_name}...")

            res = container.send_request(req.data)
            # res = {"res": 'ok'}
            req.result.set(res)

        # 3. put the container back into pool
        # function.put_container(container)
        self.put_container(container)

    # get a container from container pool
    # if there's no container in pool, return None
    def self_container(self, function):
        res = None
        print("Acquiring lock on self container")
        self.b.acquire()
        print("Acquirrd ok")
        print(f"Now the length of container pool is {len(self.container_pool) }")
        if len(self.container_pool) != 0:
            print('get container from pool of function: %s, pool size: %d',
                  function.info.function_name, len(self.container_pool))

            res = self.container_pool.pop(-1)
            self.num_exec += 1
        print("Releasing lock on self container")
        self.b.release()
        print("Released ok")
        return res

    # create a new container
    def create_container(self, function):
        # do not create new exec container
        # when the number of execs hits the limit
        """ 暂时忽略scale limit
        """
        # self.b.acquire()  # critical: missing lock may cause infinite container creation under high concurrency scenario
        # if self.num_exec + len(self.container_pool) > function.info.max_containers:
        # logging.info('hit container limit, function: %s',
        #  function.info.function_name)
        # return None
        # self.num_exec += 1
        # self.b.release()
        if len(self.candidate_containers) != 0:
            logging.info(
                f"Get candidate container of function {function.info.function_name}")
            return self.candidate_containers.pop(-1)

        try:
            # self.b.acquire()
            logging.info(f'create container of function: {function.info.function_name}',)
            container = Container.create(
                self.client, function.info.img_name, self.port_controller.get(), 'exec')
            container.img_name = function.info.img_name
            logging.info(
                f"Put candidate container of function {function.info.function_name} in to candidate_containers")
            self.candidate_containers.append(container)
        except Exception as e:
            print(e)
            self.num_exec -= 1
            return None
        self.init_container(container, function)
        # self.b.release()

        return container

    # do the function specific initialization work
    def init_container(self, container, function):
        container.init(function.info.workflow_name,
                       function.info.function_name)

    # put the container into one of the three pool, according to its attribute
    def put_container(self, container):
        self.b.acquire()
        self.container_pool.append(container)
        # print(f"There are {len(self.container_pool)} of containers in pool")
        self.num_exec -= 1
        self.b.release()

    # after the destruction of container
    # its port should be give back to port manager
    def remove_container(self, container):
        print(f'remove container group: {self.name}, pool size: {len(self.container_pool)}',)
        container.destroy()
        self.port_controller.put(container.port)

    # do the repack and cleaning work regularly
    def repack_and_clean(self):
        # print("====== repack and clean containers ======")
        # find the old containers
        old_container = []
        self.b.acquire()
        self.container_pool = clean_pool(
            self.container_pool, exec_lifetime, old_container)
        self.b.release()

        # time consuming work is put here
        for c in old_container:
            self.remove_container(c)


# life time of three different kinds of containers
exec_lifetime = 600


def clean_pool(pool, lifetime, old_container):
    cur_time = time.time()
    idx = -1
    for i, c in enumerate(pool):
        if cur_time - c.lasttime < lifetime:
            idx = i
            break
    # all containers in pool are old, or the pool is empty
    if idx < 0:
        idx = len(pool)
    old_container.extend(pool[:idx])
    return pool[idx:]
