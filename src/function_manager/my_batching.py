from copy import copy
from queue import Queue
import threading
from typing import List
from urllib import request
from function_group import FunctionGroup
import gevent
import numpy as np
import time
import copy
from function import Function
from container import Container
from request_recorder import HistoryDelay
from thread import ThreadWithReturnValue


class Batching(FunctionGroup):
    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.resp_latency = 0  # in ms
        self.containers = []
        self.batch_size = 0  # in number of request
        self.cold_start_time = 0  # in ms
        self.slack = 0  # in ms

        # Only stores the latency in last 10s
        self.history_delay = HistoryDelay()
        self.time_exec = HistoryDelay(uptate_interval=np.inf)
        self.time_cold = HistoryDelay(uptate_interval=np.inf)

        self.executing_rqs = []

    def send_request(self, function, request_id, runtime, input, output, to, keys):
        res = super().send_request(function, request_id, runtime, input, output, to, keys)
        return res

    def estimate_container(self) -> int:
        """Estimates how many containers required

        Returns:
            int: number of containers needed
        """
        if len(self.containers) == 0:
            return len(self.rq)

        total_delay = len(self.rq) * self.resp_latency

        cur_req = len(self.containers) * self.batch_size

        delay_factor = total_delay / cur_req  # divided by zero ???
        if delay_factor > self.cold_start_times.mean():
            num_containers = self.rq/cur_req

        return num_containers

    def wait_available_container(self, local_rq: List) -> List:
        """Wait for other requests to end the container occupation

        Args:
            timeout (int): We need a timeout to carry the QoS
            start_waiting (time): The time we start to wait
            function (Function): Function instance for creating container
            container_need (int): The number of containers needs to created

        Returns:
            List: Available containers
        """
        print(f"There are {len(self.executing_rqs)} of requests running")
        now = time.time()
        finished = []
        unfinished = []
        for req in self.executing_rqs:
            if req.expect_time < now:
                finished.append(req)
            else:
                unfinished.append(req)
        print(
            f"It seems there are {len(finished)} of requests have been done, and now the num of avaiable container is {len(self.container_pool)}")
        return []

    def dynamic_reactive_scaling(self, function, local_rq):
        """Create containers according to the strategy
        """
        num_containers = len(local_rq)
        container_created = 0

        # 已经创建但是未执行过请求的容器，即创建完毕但是没有放在container_pool的容器，用于将并发请求按顺序排队
        candidate_containers = []
        print(f"We need {num_containers} of containers")

        # 1. 先从container pool中获取尽量多可用的容器
        while len(self.container_pool) and container_created < num_containers:
            container = self.self_container(function=function)
            candidate_containers.append(container)
            container_created += 1

        # 2. 如果容器数量不够，则等待至容器可用
        """
        TODO 还需要量化的等待可用容器带来的内存开销
        1. 现在正在执行的请求，拥有这些请求开始的时间
        2. 根据历史执行时间，这些请求还有多久能释放容器
        3. 判断需要等待的时间，和冷启动时间比较
        """
        print(
            f"Still need more {num_containers-container_created} of containers")
        self.wait_available_container(local_rq=local_rq)

        container = None
        # 3. 创建剩下所需的容器
        while container_created < num_containers:
            while not container:
                start = time.time()
                container = self.create_container(function=function)
                cold_start = (time.time() - start) * 1000  # Coverts s to ms
                self.time_cold.append(cold_start)
                # container = self.fake_create_container(function=function)

            print(f"{container_created} of containers have been created")
            candidate_containers.append(container)
            container_created += 1
        return candidate_containers

    def dispatch_request(self):
        # Only process the request that req.processing == False
        self.b.acquire()
        local_rq = []
        for req in self.rq:
            if not req.processing:
                req.processing = True
                local_rq.append(req)
        self.b.release()
        # no request to dispatch
        if len(local_rq) == 0:
            return

        function = local_rq[0].function
        # Create or get containers
        candidate_containers = self.dynamic_reactive_scaling(
            function=function, local_rq=local_rq)

        # Map reqeusts to containers and run them
        threads = self.map_and_run_rqs(local_rq, candidate_containers)

        # Record exec time, remove running requests, and put container to pool
        self.finish_reqs(threads)

    def map_and_run_rqs(self, local_rq, candidate_containers):
        idx = 0
        # Mapping requests to containers
        c_r_mapping = {c: [] for c in candidate_containers}
        while local_rq:
            container = candidate_containers[idx]
            req = local_rq.pop(0)
            self.rq.remove(req)  # ???
            c_r_mapping[container].append(req)
            idx = (idx + 1) % len(candidate_containers)

        threads = []
        for c, reqs in c_r_mapping.items():
            t = ThreadWithReturnValue(
                target=c.send_batch_requests, args=(reqs, ))
            threads.append(t)
            t.start()
            execute_time = time.time()

            for i, req in enumerate(reqs):
                # These requests are executed one by one because of batching
                req.expect_time += execute_time * (i+1)
                self.executing_rqs.append(req)
        return threads

    def finish_reqs(self, threads):
        start = time.time()
        for t in threads:
            result = t.join()
            time_exec = (time.time() - start) * 1000  # Coverts ms to s
            self.time_exec.append(time_exec)
            # print(f"The execution times of [group {self.name}] are {self.time_exec.history_delay}")

            container = result['container']
            requests = result['requests']
            for req in requests:
                self.executing_rqs.remove(req)
            self.put_container(container)
