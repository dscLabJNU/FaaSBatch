import logging
from function_group import FunctionGroup
import numpy as np
import time
from history_record import HistoryRecord
from thread import ThreadWithReturnValue
import hashlib
from collections import defaultdict
from hash_ring import HashRing


def hash_string(s: str):
    sha1 = hashlib.sha1()
    sha1.update(s.encode('utf-8'))
    return sha1.hexdigest()


SAMPLE_RATE = 0.2
POPULAR_PERCENTAIL = 90


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

        self.hash_ring = HashRing()
        self.last_access_times = defaultdict(float)  # 存储每个req的最后访问时间
        self.iat_estimates = defaultdict(list)      # 存储每个req的IAT
        self.contaier_load = defaultdict(float)      # 每个容器处理请求的个数

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
                # 添加新创建的容器到哈希环
                self.hash_ring.add_container(container)

            candidate_containers.append(container)
            container_created += 1
            logging.info(
                f"{container_created} of containers have been created")
        return candidate_containers

    def resort_mapping(self, c_r_mapping):
        return c_r_mapping

    def select_containers_by_aws_arguments(self, local_rq):
        c_r_mapping = defaultdict(list)

        # Step 1: Collect all possible containers for each aws_boto3_argument
        aws_arg_to_containers = defaultdict(list)
        for req in local_rq:
            azure_data = req.data.get('azure_data', {})
            aws_boto3_argument = azure_data.get('aws_boto3', {})
            if aws_boto3_argument:
                hash_aws_arg = hash_string(str(aws_boto3_argument))
                containers = self.cached_key_map.get(hash_aws_arg, [])
                aws_arg_to_containers[hash_aws_arg].extend(containers)

        # Step 2: Compute the load of each container
        container_load = defaultdict(int)
        for containers in aws_arg_to_containers.values():
            for container in containers:
                container_load[container] += 1

        # Step 3: Assign each request to the container with the least load
        for req in local_rq:
            azure_data = req.data.get('azure_data', {})
            aws_boto3_argument = azure_data.get('aws_boto3', {})
            if aws_boto3_argument:
                hash_aws_arg = hash_string(str(aws_boto3_argument))
                containers = aws_arg_to_containers[hash_aws_arg]
                if containers:
                    # Find the container with the least load
                    min_load_container = min(
                        containers, key=lambda c: container_load[c])
                    c_r_mapping[min_load_container].append(req)
                    container_load[min_load_container] += 1
                    print(
                        f"Plan sending {hash_aws_arg} to {min_load_container.container.id}")

        print(f"container->req mapping: {c_r_mapping}")

        # balance the mapping relationship
        return self.resort_mapping(c_r_mapping)

    def get_aws_arg_arrival_rate(self, hash_aws_arg):
        # 从记录的 IAT 估计中获取给定 hash_aws_arg 的 IAT
        iat_estimate = self.iat_estimates.get(hash_aws_arg, 0)

        # 到达率是到达间隔的倒数
        arrival_rate = 1 / iat_estimate if iat_estimate > 0 else 0

        return arrival_rate

    def identify_popular_requests(self, local_rq):
        popular_functions = set()

        for req in local_rq:
            azure_data = req.data.get('azure_data', {})
            aws_boto3_argument = azure_data.get('aws_boto3', {})
            if aws_boto3_argument:
                hash_aws_arg = hash_string(str(aws_boto3_argument))
                # arrival_time = req.arrival
                arrival_time = time.time()

                if np.random.rand() < SAMPLE_RATE:
                    last_access_time = self.last_access_times.get(
                        hash_aws_arg, arrival_time)
                    current_iat = arrival_time - last_access_time
                    iat_estimate = self.iat_estimates.get(
                        hash_aws_arg, current_iat)
                    iat_estimate = 0.5 * iat_estimate + 0.5 * current_iat

                    self.iat_estimates[hash_aws_arg] = iat_estimate
                    self.last_access_times[hash_aws_arg] = arrival_time

        iat_values = list(self.iat_estimates.values())
        if iat_values:
            top_p_percentile_iat = np.percentile(
                iat_values, POPULAR_PERCENTAIL)
            # print(f"iat_values: {iat_values}, top_p_percentile_iat:{top_p_percentile_iat}")
            popular_functions = {
                func for func, iat in self.iat_estimates.items() if iat < top_p_percentile_iat}

        return popular_functions

    def get_container_load(self, container):
        return self.contaier_load[container]

    def select_containers_with_hash_ring(self, local_rq):
        c_r_mapping = defaultdict(list)

        for req in local_rq:
            print(f"this request arrived at: {req.arrival}")
            azure_data = req.data.get('azure_data', {})
            aws_boto3_argument = azure_data.get('aws_boto3', {})
            if aws_boto3_argument:
                hash_aws_arg = hash_string(str(aws_boto3_argument))
                container = self.hash_ring.get_container(hash_aws_arg)
                if container:
                    c_r_mapping[container].append(req)
        return c_r_mapping

    def select_containers_by_hash_ring(self, local_rq):
        popular_functions = self.identify_popular_requests(local_rq)
        print(f"popular_functions: {popular_functions}")
        c_r_mapping = self.select_containers_with_hash_ring(local_rq)
        return c_r_mapping

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
        # c_r_mapping = self.select_containers_by_aws_arguments(local_rq)
        c_r_mapping = self.select_containers_by_hash_ring(local_rq)

        print(f"c_r_mapping: {c_r_mapping}")
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
            self.contaier_load[c] += len(reqs)
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
