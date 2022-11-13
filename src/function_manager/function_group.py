import logging
import time
import uuid
import threading

from gevent import event
from gevent.lock import BoundedSemaphore
from container import Container

"""
Data structure for request info
"""


class RequestInfo:
    def __init__(self, function, request_id, data, function_id):
        self.function = function
        self.request_id = request_id
        self.data = data
        self.result = event.AsyncResult()
        # True if request is being process
        self.processing = False
        self.function_id = function_id

        self.arrival = time.time()
        self.start_exec = 0  # Timestamp as the execution started
        self.end_exec = 0  # Timestamp as the exeuction end
        self.expect_end_ts = 0  # Expected finish timestamp

        self.defer = None  # Defer the expect_end_ts close to the end_ts

    def get_schedule_time(self):
        if self.start_exec > 0:
            return (self.start_exec - self.arrival) * 1000  # Converts s to ms
        else:
            raise ValueError("This request has not been executed")


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

        self.b = BoundedSemaphore()

    def init_logs(self, invocation_log, function_load_log):
        """
            schedule_time:  The time from receiving the request to sending the request to the container,
                including cold start and time overhead of the strategy
            queue_time:     Queue time of the request in the container
            exec_time:      CPU time
            used_memory:    Memory consumption for the io functions
        """
        print(f"function,schedule_time(ms),exec_time(ms),queue_time(ms),used_memory(MB)",
              file=invocation_log, flush=True)
        print("function,load", file=function_load_log, flush=True)

    # put the request into request queue
    def send_request(self, function, request_id, runtime, input, output, to, keys, azure_data=None):
        function_id = function.info.function_name + "-" + str(uuid.uuid4())
        data = {'request_id': request_id, 'runtime': runtime,
                'input': input, 'output': output, 'to': to, 'keys': keys, "azure_data": azure_data,
                "function_id": function_id}
        req = RequestInfo(function, request_id, data, function_id)
        self.rq.append(req)
        res = req.result.get()
        return res

    # receive a request from upper layer
    def dispatch_request(self, container=None):
        pass

    # get a container from container pool
    # if there's no container in pool, return None
    def self_container(self, function):
        res = None
        print(
            f"Now the length of container pool is {len(self.container_pool) }")
        self.b.acquire()
        if len(self.container_pool) != 0:
            print('get container from pool of function: %s, pool size: %d',
                  function.info.function_name, len(self.container_pool))

            res = self.container_pool.pop(-1)
            self.num_exec += 1
        self.b.release()
        return res

    def create_containers_in_blocking(self, num_containers, function):
        """Creating containers in a blocking way, i.e., one by one
        Containers creation can be in blocking way or parallel way, 
        experimental result shows that a blocking way gets better performance
        """
        if num_containers <= 0:
            return []
        containers = []
        container_created = 0
        while container_created < num_containers:
            container = None
            while not container:
                start = time.time()
                container = self.create_container(function=function)
                cold_start = (time.time() - start) * 1000  # Coverts s to ms
                self.time_cold.append(cold_start)

            containers.append(container)
            container_created += 1
            logging.info(
                f"{container_created} of containers have been created")
        return containers

    def create_containers_in_parallel(self, num_containers, function):
        """Creating containers in a parallel fashion, using multi-threadings
        """
        if num_containers <= 0:
            return []
        containers = []
        logging.info(
            f"Ready for creating {num_containers} of containers in parallel")
        containers = self.parallel_create_containers(
            num_containers=num_containers, function=function, containers_parallel=containers)
        if num_containers != len(containers):
            raise ValueError(
                "Number of container needed and that of created NOT equal!!!")
        logging.info(
            f"Created {len(containers)} of containers in parallel")
        return containers

    def create_container_in_thread(self, function, containers_parallel):
        container = None
        while not container:
            container = self.create_container(function=function)

        containers_parallel.append(container)

    def parallel_create_containers(self, num_containers, function, containers_parallel):
        threads = []
        for _ in range(num_containers):
            t = threading.Thread(
                target=self.create_container_in_thread, args=(function, containers_parallel,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        return containers_parallel

    def create_container(self, function, bind_cpus=None):
        """Creating a new container
        """
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

        try:
            # self.b.acquire()
            logging.info(
                f'create container of function: {function.info.function_name}',)
            container = Container.create(
                self.client, function.info.img_name, self.port_controller.get(), 'exec', bind_cpus)
            container.img_name = function.info.img_name
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
        print(f"Put {container.container.name} into container pool")
        self.container_pool.append(container)
        # print(f"There are {len(self.container_pool)} of containers in pool")
        self.num_exec -= 1
        self.b.release()

    # after the destruction of container
    # its port should be give back to port manager
    def remove_container(self, container):
        print(
            f'remove container group: {self.name}, pool size: {len(self.container_pool)}',)
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

    def record_info(self, req, log_file):
        print(
            f"request {req.function.info.function_name} is done, recording the execution infomation...")
        self.historical_reqs.append(req)
        self.history_duration.append(req.duration)
        result = req.result.get()
        print(f"Result is: {result}")
        exec_time = result['exec_time']
        # No queuing in our proposed method, all requests are invoked in parallel
        queue_time = result.get('queue_time', 0)
        # Only available in client creation evaluation
        mem_used = result.get("mem_used", None)
        print(f"{req.function.info.function_name},{req.get_schedule_time()},{exec_time},{queue_time},{mem_used}",
              file=log_file, flush=True)
        if req.defer:
            self.defer_times.append(req.defer)


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
