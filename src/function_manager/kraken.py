from copy import copy
from function_group import FunctionGroup
import gevent
import numpy as np
import time
import copy
from request_recorder import HistoryDelay

class Kraken(FunctionGroup):
    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.batch_size = 4

    def send_request(self, function, request_id, runtime, input, output, to, keys):
        res = super().send_request(function, request_id, runtime, input, output, to, keys)
        return res

    def estimate_container(self) -> int:
        """Estimates how many containers required

        Returns:
            list: current requests
        """
        
        num_handle_rq = len(self.rq)
        """
        We get or create $num_containers for handler $num_handle_rq.
        self.rq may update during this procedure, thus we leave the remaining requests to be handled in next round
        """
        num_containers = (num_handle_rq // self.batch_size) or num_handle_rq
        return num_containers, num_handle_rq

    def dynamic_reactive_scaling(self, function):
        """Create containers according to the strategy
        """
        num_containers, num_handle_rq = self.estimate_container()


        container_created = 0
        candidate_containers = []
        while container_created < num_containers:
            container = self.self_container(function=function)
            while not container:
                container = self.create_container(function=function)
            # the number of exec container hits limit
            if container is None:
                self.num_processing -= 1
                print("container is None")
                exit(1)
                return

            candidate_containers.append(container)
            container_created += 1
        return candidate_containers, num_handle_rq
        
    def dispatch_request(self, container=None):
        # no request to dispatch
        if len(self.rq) - self.num_processing == 0:
            return
        if len(self.rq) == 0:
            return 0
        
        self.num_processing += 1
        function = self.rq[0].function

        # Create containers according to Fifer strategy
        candidate_containers, num_handle_rq = self.dynamic_reactive_scaling(function=function)
        print(f"Having {len(candidate_containers)} containers for {num_handle_rq} of requests")

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

            res = container.send_request(req.data)
            # res = {"res": 'ok'}
            req.result.set(res)
            idx = (idx + 1) % len(candidate_containers)

            self.put_container(container)
