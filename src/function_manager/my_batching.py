from copy import copy
from queue import Queue
import threading
from function_group import FunctionGroup
import gevent
import numpy as np
import time
import copy
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

    def dynamic_reactive_scaling(self, function, local_rq):
        """Create containers according to the strategy
        """
        num_containers = len(local_rq) // 2 or len(local_rq)
        container_created = 0

        # 已经创建但是未执行过请求的容器，即创建完毕但是没有放在container_pool的容器，用于将并发请求按顺序排队
        candidate_containers = []
        print(f"We need {num_containers} of containers")

        while container_created != num_containers:
            # container = self.fake_get_container(function=function)
            container = self.self_container(function=function)
            while not container:
                container = self.create_container(function=function)
                # container = self.fake_create_container(function=function)
            print(f"{container_created} of containers have been created")
            candidate_containers.append(container)
            container_created += 1
        return candidate_containers

    def dispatch_request(self, container=None):
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
            t = ThreadWithReturnValue(target=c.send_batch_requests, args=(reqs, ))
            threads.append(t)
            t.start()

        for t in threads:
            container = t.join()
            print(f"The return container is {container}")
            self.put_container(container)
