import logging
from function_group import FunctionGroup
import numpy as np
import time
from history_record import HistoryRecord
from thread import ThreadWithReturnValue
import hashlib
from collections import defaultdict


def hash_string(s: str):
    sha1 = hashlib.sha1()
    sha1.update(s.encode('utf-8'))
    return sha1.hexdigest()


class FaaSBatch(FunctionGroup):
    log_file = None

    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.history_duration = HistoryRecord(update_interval=np.inf)  # in ms
        self.time_cold = HistoryRecord(update_interval=np.inf)
        self.defer_times = HistoryRecord(update_interval=np.inf)
        self.executing_rqs = []
        self.historical_reqs = []
        # container_id -> cached_keys
        self.cached_key_map = defaultdict(lambda: [])

        if not FaaSBatch.log_file:
            FaaSBatch.log_file = open(
                "./tmp/latency_amplification_FaaSBatch.csv", 'w')
            FaaSBatch.function_load_log = open(
                "./tmp/function_load_FaaSBatch.csv", "w")
            FaaSBatch.hit_rate_log = open(
                "./tmp/hit_rate_FaaSBatch.csv", "w")
            self.init_logs(invocation_log=FaaSBatch.log_file,
                           function_load_log=FaaSBatch.function_load_log,
                           hit_rate_log=FaaSBatch.hit_rate_log)

    def send_request(self, function, request_id, runtime, input, output, to, keys, duration=None):
        res = super().send_request(function, request_id,
                                   runtime, input, output, to, keys, duration)
        return res

    def estimate_container(self, local_rq) -> int:
        """Estimates how many containers is required
        Returns:
            int: number of containers needed
        """
        return 1

    def dynamic_reactive_scaling(self, function, local_rq):
        """Create containers according to the strategy
        """
        num_containers = self.estimate_container(local_rq=local_rq)
        concurrency = len(local_rq)
        container_created = 0

        # 已经创建但是未执行过请求的容器，即创建完毕但是没有放在container_pool的容器，用于将并发请求按顺序排队
        candidate_containers = []
        print(f"We need {num_containers} of containers")

        # 1. 先从container pool中获取尽量多可用的容器
        while len(self.container_pool) and container_created < num_containers:
            container = self.self_container(function=function)
            candidate_containers.append(container)
            container_created += 1

        # it contains the cache_strategy (request_data['cache_strategy'])
        request_data = local_rq[0].data
        # 2. 创建剩下所需的容器
        while container_created < num_containers:
            container = None
            while not container:
                start = time.time()
                container = self.create_container(
                    function=function, extra_data=request_data)
                cold_start = (time.time() - start) * 1000  # Coverts s to ms
                self.time_cold.append(cold_start)

            candidate_containers.append(container)
            container_created += 1
            logging.info(
                f"{container_created} of containers have been created")
        return candidate_containers

    def resort_mapping(self, c_r_mapping):
        return c_r_mapping

    def select_containers_by_aws_arguments(self, local_rq):
        c_r_mapping = defaultdict(lambda: [])
        for req in local_rq:
            azure_data = req.data.get('azure_data', {})
            aws_boto3_argument = azure_data.get('aws_boto3', {})
            if aws_boto3_argument:
                hash_aws_arg = hash_string(str(aws_boto3_argument))

                # mapping container->req by ananlyzing the aws_arguments
                containers = self.cached_key_map.get(hash_aws_arg, [])
                for container in containers:
                    c_r_mapping[container].append(req)
                    print(
                        f"Plan sending {hash_aws_arg} to {container.container.id}")

        print(f"container->req mapping: {c_r_mapping}")

        # balance the mapping relationship
        return self.resort_mapping(c_r_mapping)

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

        # Map reqeusts to containers and run them
        c_r_mapping = self.select_containers_by_aws_arguments(local_rq)
        print(f"c_r_mapping: {c_r_mapping}, {not c_r_mapping}")
        if not c_r_mapping:
            # Create or get containers
            candidate_containers = self.dynamic_reactive_scaling(
                function=function, local_rq=local_rq)
            c_r_mapping = self.normal_mapping(local_rq, candidate_containers)
        threads = self.execute_requests(c_r_mapping)

        # Record exec time, remove running requests, and put container to pool
        # Note that one thread may contains several request results
        self.finish_threads(threads)

    def execute_requests(self, c_r_mapping):
        threads = []
        for c, reqs in c_r_mapping.items():
            t = ThreadWithReturnValue(
                target=c.send_batch_requests, args=(reqs, self.executing_rqs,))
            threads.append(t)
            t.start()
        return threads

    def normal_mapping(self, local_rq, candidate_containers):
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
        return c_r_mapping

    def finish_threads(self, threads):
        for t in threads:
            print(f"Finising thread {t}")
            result = t.join()

            container = result['container']
            requests = result['requests']
            for req in requests:
                self.executing_rqs.remove(req)
            self.put_container(container)

            # core_manager.release_busy_cores(container)
            for req in requests:
                self.record_info(req=req, log_file=FaaSBatch.log_file)

        # Only report the latest info.
        # TODO maintain a timestamp ??
        self.update_global_keys(
            cached_keys=result['cached_keys'], container=container)

    def update_global_keys(self, cached_keys, container):
        """
        Mapping:
            cached_key1 -> container1
            cached_key2 -> container1
        """
        if not cached_keys:
            return
        self.b.acquire()
        for aws_key in cached_keys:
            print(f"Mapping {aws_key} to container {container}")
            self.cached_key_map[aws_key].append(container)
        self.b.release()
