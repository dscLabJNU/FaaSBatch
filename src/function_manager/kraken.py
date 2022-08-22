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
        self.batch_size = 2

    def send_request(self, function, request_id, runtime, input, output, to, keys):
        res = super().send_request(function, request_id, runtime, input, output, to, keys)
        return res

    def estimate_container(self, cur_requests) -> int:
        """Estimates how many containers required

        Returns:
            list: current requests
        """

        return (len(cur_requests) // self.batch_size) or len(cur_requests)

    def dynamic_reactive_scaling(self, function, cur_requests):
        """Create containers according to the strategy
        """
        num_containers = self.estimate_container(cur_requests)


        container_created = 0
        candidate_containers = []
        while container_created < num_containers:
            container = self.self_container(function=function)
            while not container:
                container = self.create_container(function=function)
            # the number of exec container hits limit
            if container is None:
                self.num_processing -= 1
                return

            candidate_containers.append(container)
            container_created += 1
        return candidate_containers
        
    def dispatch_request(self, container=None):
        print("Kraken...")
        # no request to dispatch
        cur_requests = copy.deepcopy(self.rq)
        if len(cur_requests) - self.num_processing == 0:
            return
        if len(cur_requests) == 0:
            return 0
        self.num_processing += 1
        function = cur_requests[0].function

        # Create containers according to Fifer strategy
        candidate_containers = self.dynamic_reactive_scaling(function=function)
        print(
            f"We now have {len(candidate_containers)} of candidate containers")

        idx = 0
        # Mapping requests to containers
        while cur_requests:
            self.num_processing -= 1
            print(
                f"The length of rq in this {self.name} group is {len(self.rq)}")

            req = cur_requests.pop(0)
            container = candidate_containers[idx]
            print(
                f"Ready for batching request {req.function.info.function_name} in container {container.img_name}...")

            res = container.send_request(req.data)
            # res = {"res": 'ok'}
            req.result.set(res)
            idx = (idx + 1) % len(candidate_containers)

            self.put_container(container)
