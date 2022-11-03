import logging
from function_group import FunctionGroup
import numpy as np
from history_record import HistoryRecord
from thread import ThreadWithReturnValue
# from core_manager import CoreManaerger
# num_cores = multiprocessing.cpu_count()
# # idel_cores = [i for i in range(num_cores)]
# core_manager = CoreManaerger(
#     available_cores=[str(i) for i in range(num_cores)])


class SFS(FunctionGroup):
    """
    CoreManager is not working in this strategy, we let Linux OS itself controls the mapping of docker container and CPU core

    Args:
        FunctionGroup: Each FunctionGroup represents a typical function

    """
    log_file = None

    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.resp_latency = 0  # in ms
        self.containers = []
        self.batch_size = 0  # in number of request
        self.cold_start_time = 0  # in ms
        self.slack = 0  # in ms

        self.history_duration = HistoryRecord(update_interval=np.inf)  # in ms
        self.time_cold = HistoryRecord(update_interval=np.inf)
        self.defer_times = HistoryRecord(update_interval=np.inf)
        self.executing_rqs = []
        self.historical_reqs = []

        if not SFS.log_file:
            SFS.log_file = open(
                "./tmp/latency_amplification_SFS.csv", 'w')
            """
            schedule_time:  The time from receiving the request to sending the request to the container,
                including cold start and time overhead of the strategy
            queue_time:     Queue time of the request in the container
            exec_time:      CPU time
            """
            print(f"function,schedule_time(ms),exec_time(ms),queue_time(ms)",
                  file=SFS.log_file, flush=True)

    def send_request(self, function, request_id, runtime, input, output, to, keys, duration=None):
        res = super().send_request(function, request_id,
                                   runtime, input, output, to, keys, duration)
        return res

    def estimate_container(self, local_rq) -> int:
        """Estimates how many containers is required
        Returns:
            int: number of containers needed
        """
        return len(local_rq)

    def dynamic_reactive_scaling(self, function, local_rq):
        """Create containers according to the strategy
        """
        num_containers = self.estimate_container(local_rq=local_rq)
        concurrency = len(local_rq)
        container_retrieved = 0

        # 已经创建但是未执行过请求的容器，即创建完毕但是没有放在container_pool的容器，用于将并发请求按顺序排队
        candidate_containers = []
        logging.info(f"We need {num_containers} of containers")

        # 1. Obtain as many containers as possible from the container pool
        while len(self.container_pool) and container_retrieved < num_containers:
            container = self.self_container(function=function)
            candidate_containers.append(container)
            container_retrieved += 1
        logging.info(f"Get {container_retrieved} of containers from the pool")

        # 2. Create remaining containers
        new_containers = self.create_containers_in_blocking(
            num_containers=num_containers - container_retrieved, function=function)

        candidate_containers.extend(new_containers)
        if len(candidate_containers) != num_containers:
            raise ValueError(
                f"We want {num_containers} of containers, but there are {len(candidate_containers)}")
        return candidate_containers

    def dispatch_request(self):
        # Only process the request that req.processing == False
        self.b.acquire()
        local_rq = []
        for req in self.rq:
            if not req.processing:
                req.processing = True
                req.data['azure_data'].update({"activate_SFS": True})
                print(f"req {req.data['azure_data']}")
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
        # Note that one thread may contains several request results
        self.finish_threads(threads)

    def map_and_run_rqs(self, local_rq, candidate_containers):
        idx = 0
        # Mapping requests to containers
        print(
            f"Mapping {len(local_rq)} of requests to {len(candidate_containers)} of containers")
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
                target=c.send_batch_requests, args=(reqs, self.executing_rqs,))
            threads.append(t)
            t.start()
        return threads

    def finish_threads(self, threads):
        for t in threads:
            print(f"Finising thread {t}")
            result = t.join()

            container = result['container']
            requests = result['requests']
            for req in requests:
                self.executing_rqs.remove(req)
            self.put_container(container)

            for req in requests:
                self.record_info(req)

    def record_info(self, req):
        print(
            f"request {req.function.info.function_name} is done, recording the execution infomation...")
        self.historical_reqs.append(req)
        self.history_duration.append(req.duration)
        result = req.result.get()
        exec_time = result['exec_time']
        print(f"exec_time vs. duration: {exec_time}:{req.duration}")
        queue_time = result.get('queue_time', 0)
        print(f"{req.function.info.function_name},{req.get_schedule_time()},{exec_time},{queue_time}",
              file=SFS.log_file, flush=True)
        if req.defer:
            self.defer_times.append(req.defer)
