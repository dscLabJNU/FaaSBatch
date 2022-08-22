from copy import copy
from function_group import FunctionGroup
import gevent
import numpy as np
import time
import copy
from request_recorder import HistoryDelay

log_file = open(f"./time_comparation_Fifer.csv", 'w')
print("group_name,exec_time,cold_time", flush=True, file=log_file)


class Fifer(FunctionGroup):
    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.resp_latency = 0  # in ms
        self.containers = []
        self.batch_size = 0  # in number of request
        self.slack = 0  # in ms

        # Only stores the latency in last #HistoryDelay.update_interval seconds
        self.time_exec = HistoryDelay()
        self.time_cold = HistoryDelay()

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

    def dynamic_reactive_scaling(self, function):
        """Create containers according to the Fifer strategy
        """
        time_exec = self.time_exec.get_last10s_delay()
        time_cold = self.time_cold.get_last10s_delay()
        print(f"{self.name},{time_exec},{time_cold}",
              flush=True, file=log_file)

        self.resp_latency = 5 * self.time_exec.get_max() or 1000  # in ms
        self.slack = self.resp_latency - self.time_exec.get_last()

        print(
            f"delay >= slack? {time_exec>=self.slack},delay = {time_exec}, slack = {self.slack}")

        """
        We get or create $num_containers for handler $num_handle_rq.
        self.rq may update during this procedure, thus we leave the remaining requests to be handled in next round
        """
        num_handle_rq = len(self.rq)
        num_containers = num_handle_rq

        if time_exec >= self.slack:
            num_containers = self.estimate_container()

        container_created = 0
        candidate_containers = []
        while container_created != num_containers:
            container = self.self_container(function=function)
            while not container:
                start = time.time()
                container = self.create_container(function=function)
                cold_start = (time.time() - start) * 1000  # converts s to ms
                self.time_cold.append(cold_start)
            # the number of exec container hits limit
            if container is None:
                self.num_processing -= 1
                return

            candidate_containers.append(container)
            container_created += 1
        return candidate_containers, num_handle_rq

    def dispatch_request(self, container=None):
        # no request to dispatch
        if len(self.rq) - self.num_processing == 0:
            return
        if len(self.rq) == 0:
            return
        self.num_processing += 1
        function = self.rq[0].function

        # Create containers according to Fifer strategy
        candidate_containers, num_handle_rq = self.dynamic_reactive_scaling(
            function=function)
        print(f"Recieved {len(self.rq)} of requests...")
        print(f"There are {len(candidate_containers)} for {num_handle_rq} requests")

        idx = 0
        # Mapping requests to containers
        while self.rq:
            self.num_processing -= 1
            print(
                f"The length of rq in this {self.name} group is {len(self.rq)}")

            if num_handle_rq == 0:
                print("We handled enough number of requests")
                return
            num_handle_rq -= 1
            req = self.rq.pop(0)
            container = candidate_containers[idx]
            # print(f"Ready for batching request {req.function.info.function_name} in container {container.img_name}...")

            start = time.time()
            res = container.send_request(req.data)
            exec_delay = (time.time() - start) * 1000  # converts s to ms
            self.time_exec.append(exec_delay)

            req.result.set(res)
            idx = (idx + 1) % len(candidate_containers)

            self.put_container(container)
