import logging
from function_group import FunctionGroup
import numpy as np
import time
from history_record import HistoryRecord
from thread import ThreadWithReturnValue
import sys
import os
import pandas as pd
import math
sys.path.append('../../config')
import config
# from core_manager import CoreManaerger
# num_cores = multiprocessing.cpu_count()
# # idel_cores = [i for i in range(num_cores)]
# core_manager = CoreManaerger(
#     available_cores=[str(i) for i in range(num_cores)])


def read_function_load():
    batching_path = config.PROJECT_PATH
    csv = f"{batching_path}/src/workflow_manager/tmp/function_load.csv"
    if not os.path.exists(csv):
        raise ValueError(
            "Cannot find function_load.csv. Please executes baseline strategy according to the README.md")

    df_baseline = pd.read_csv(csv)
    groupby_func = df_baseline.groupby("function")
    function_load = {}
    for func, info in groupby_func:
        function_load[func] = list(info['load'])
    return function_load


class Kraken(FunctionGroup):
    """
    CoreManager is not working in this strategy, we let Linux OS itself controls the mapping of docker container and CPU core

    Args:
        FunctionGroup: Each FunctionGroup represents a typical function

    """
    log_file = None
    function_load = {}

    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.resp_latency = 0  # in ms
        self.containers = []

        self.history_duration = HistoryRecord(update_interval=np.inf)  # in ms
        self.time_cold = HistoryRecord(update_interval=np.inf)
        self.defer_times = HistoryRecord(update_interval=np.inf)
        self.executing_rqs = []
        self.historical_reqs = []

        """
        Parameter "stage_SLO" in below is used to batching requests
            We evaluate the SLO for each function by using the 98-percentail latency generated in baseline stragety,
        where the baseline strategy spawns a single container to serve each incoming request        
        """
        self.stage_SLO = {}
        for function in functions:
            function_name = function.info.function_name
            # It is possible that not all functions have been run in the baseline policy
            if function_name in config.FUNCTION_SLOS.keys():
                self.stage_SLO[function_name] = config.FUNCTION_SLOS[function_name]

        if not Kraken.log_file:
            Kraken.log_file = open(
                "./tmp/latency_amplification_kraken.csv", 'w')
            print(f"function,duration(ms)",
                  file=Kraken.log_file, flush=True)
            # Note that we will only do this once when initializing the Class
            Kraken.function_load = read_function_load()

    def send_request(self, function, request_id, runtime, input, output, to, keys, duration=None):
        res = super().send_request(function, request_id,
                                   runtime, input, output, to, keys, duration)
        return res

    def predict_load(self, function_name, current_load):
        # We idealize that the Kraken prediction hit rate is 100%,
        # so we directly read the function load recorded in the baseline policy
        return Kraken.function_load[function_name].pop(0)

    def estimate_container(self, local_rq, function) -> int:
        """Estimates how many containers is required
        Returns:
            int: number of containers needed
        """
        avg_duration = self.history_duration.get_mean()
        if not avg_duration:
            logging.info(f"Not avg. duration yet")
            return len(local_rq)

        function_name = function.info.function_name
        batch_size = math.floor(self.stage_SLO[function_name] / avg_duration)

        current_load = len(local_rq)
        # Is it reasonable to use time series to predict such widely varying functional loads???
        predict_load = self.predict_load(function_name, current_load)

        # batches = 0 if predict_load is zero, because some functions may have only one invocation
        batches = math.ceil(predict_load / batch_size) or 1

        logging.info(
            f"avg. duration is {avg_duration}, now set the batch size as {batches}")
        logging.info(
            f"Number of containers estimated by Kraken is: {batches}")

        return batches

    def dynamic_reactive_scaling(self, function, local_rq):
        """Create containers according to the strategy
        """
        num_containers = self.estimate_container(
            local_rq=local_rq, function=function)
        container_created = 0

        # 已经创建但是未执行过请求的容器，即创建完毕但是没有放在container_pool的容器，用于将并发请求按顺序排队
        candidate_containers = []
        print(f"We need {num_containers} of containers")

        # 1. 先从container pool中获取尽量多可用的容器
        while len(self.container_pool) and container_created < num_containers:
            container = self.self_container(function=function)
            candidate_containers.append(container)
            container_created += 1

        # 2. 创建剩下所需的容器
        while container_created < num_containers:
            container = None
            while not container:
                start = time.time()
                container = self.create_container(function=function)
                cold_start = (time.time() - start) * 1000  # Coverts s to ms
                self.time_cold.append(cold_start)

            candidate_containers.append(container)
            container_created += 1
            logging.info(
                f"{container_created} of containers have been created")
        return candidate_containers

    def reactive_scaling(self, candidate_containers):
        """scale containers up or down in response to request overloading at 
        containers under-provisioning and container over-provisioning, respectively.
        """
        # We do nothing since we idealize that the Kraken prediction hit rate is 100%,
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
        if "cpu_optimize" in function.info.function_name:
            raise ValueError(
                "Wrong function type (cpu_optimize) for Kraken strategy")
        # Create or get containers
        candidate_containers = self.dynamic_reactive_scaling(
            function=function, local_rq=local_rq)

        # Reactive Scaling
        candidate_containers = self.reactive_scaling(candidate_containers)

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
        print(f"{req.function.info.function_name},{req.duration}",
              file=Kraken.log_file, flush=True)
        if req.defer:
            self.defer_times.append(req.defer)
