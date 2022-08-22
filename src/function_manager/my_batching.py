from copy import copy
from function_group import FunctionGroup
import gevent
import numpy as np
import time
import copy
from request_recorder import HistoryDelay

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
        start = time.time()
        res = super().send_request(function, request_id, runtime, input, output, to, keys)
        delay = (time.time() - start) * 1000  # converts s to ms
        self.history_delay.append(delay)
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

    def dynamic_reactive_scaling(self, function):
        """Create containers according to the strategy
        """
        delay = self.history_delay.get_last10s_delay()

        self.resp_latency = 5 * self.history_delay.get_max() or 1000  # in ms
        self.slack = self.resp_latency - self.history_delay.get_last()

        num_containers = len(self.rq)
        if delay >= self.slack:
            num_containers = self.estimate_container()

        container_created = 0

        while container_created != num_containers:
            container = self.self_container(function=function)
            while not container:
                container = self.create_container(function=function)
            # the number of exec container hits limit
            if container is None:
                self.num_processing -= 1
                return

            self.candidate_containers.append(container)
            container_created += 1

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

        # Create containers according to Fifer strategy
        self.dynamic_reactive_scaling(function=function)
        print(
            f"We now have {len(self.candidate_containers)} of candidate containers")

        idx = 0
        # Mapping requests to containers
        while self.rq:
            self.num_processing -= 1
            print(
                f"The length of rq in this {self.name} group is {len(self.rq)}")

            req = self.rq.pop(0)
            container = self.candidate_containers[idx]
            print(
                f"Ready for batching request {req.function.info.function_name} in container {container.img_name}...")

            res = container.send_request(req.data)
            # res = {"res": 'ok'}
            req.result.set(res)
            idx = (idx + 1) % len(self.candidate_containers)

            self.put_container(container)
