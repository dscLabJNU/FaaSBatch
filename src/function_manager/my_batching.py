import logging
import multiprocessing
from typing import List
from function_group import FunctionGroup
import numpy as np
import time
from request_recorder import HistoryDelay
from thread import ThreadWithReturnValue
import uuid
from core_manager import CoreManaerger
num_cores = multiprocessing.cpu_count()
# idel_cores = [i for i in range(num_cores)]
core_manager = CoreManaerger(
    core_ids=[str(i) for i in range(num_cores)])


class Batching(FunctionGroup):
    log_file_flag = False

    def __init__(self, name, functions, docker_client, port_controller) -> None:
        super().__init__(name, functions, docker_client, port_controller)
        self.resp_latency = 0  # in ms
        self.containers = []
        self.batch_size = 0  # in number of request
        self.cold_start_time = 0  # in ms
        self.slack = 0  # in ms

        self.history_duration = HistoryDelay(update_interval=np.inf)  # in ms
        self.time_cold = HistoryDelay(update_interval=np.inf)
        self.defer_times = HistoryDelay(update_interval=np.inf)
        self.executing_rqs = []
        self.historical_reqs = []

        if not Batching.log_file_flag:
            global log_file
            log_file = open(
                "./tmp/latency_amplification_my_batching.csv", 'w')
            print(f"function,duration(ms)", file=log_file, flush=True)
            Batching.log_file_flag = True

    def send_request(self, function, request_id, runtime, input, output, to, keys, duration=None):
        res = super().send_request(function, request_id,
                                   runtime, input, output, to, keys, duration)
        return res

    def gradual_adapt_defer(self, diff, predict_early):
        """渐进适配defer，每一次加self.defer_times.get_mean()的1/i, i = 1, 2, 3 ...
        Args:
            diff (float): 预期结束时间戳和实际结束时间戳的差值
            predict_early (bool): 预期结束时间戳早于实际结束时间戳
        """
        divide_factor = 1
        defer = diff
        while predict_early:
            print(f"预计完成时间比实际完成时间{'早了'if defer<0 else '晚了'}{abs(defer)}")
            if self.defer_times:
                print(f"defer +={ self.defer_times.get_mean()/divide_factor}")
                defer += self.defer_times.get_mean()/divide_factor
            else:
                print(f"defer += {0.2 / divide_factor} or 0.2")
                defer += 0.2 / divide_factor or 0.2
            predict_early = True if defer < 0 else False
            divide_factor += 1
            time.sleep(1)

        # 恢复原来defer的意义
        return defer - diff

    def adjust_by_defer(self):

        for history_req in self.historical_reqs:
            diff = history_req.expect_end_ts - history_req.end_ts
            print(f"diff = {history_req.expect_end_ts} - {history_req.end_ts}")
            predict_early = True if diff < 0 else False

            defer = self.gradual_adapt_defer(diff, predict_early)
            if defer + diff > 0:
                break

        exp_end_times = [req.expect_end_ts for req in self.executing_rqs]
        for req in self.executing_rqs:

            req.defer = defer
        return list(map(lambda x: x+defer, exp_end_times))

    def analyze_history(self):
        """Analyze the execution history and
        get the expcted end times of all running requests

        Returns:
            List: expcted end times  of all running requests
        """
        if len(self.historical_reqs) == 0:
            print("This type of request has not been executed, can't analyze the history")
            return None
        # print(f"Now we analyzing the execution history...")
        print(
            f"History duration of {self.name}: {self.history_duration.values}")
        std_duration = self.history_duration.get_std()
        # Use ms as the unit of duration
        if std_duration > 350:
            print(
                f"Historical data is too volatile, std of that is {std_duration}")
            # 历史数据波动太大
            return None

        avg_duration = self.history_duration.get_mean()
        exp_end_times = []
        for req in self.executing_rqs:
            if not req.start_ts:
                print("req.start_ts == 0 shoud be never happend...")
                exit(1)
            req.expect_end_ts = req.start_ts + avg_duration
            exp_end_times.append(req.expect_end_ts)
        # Adjust defer factor by analyzing the diff between historical exp_end_time and end_ts
        # exp_end_times = self.adjust_by_defer()

        return exp_end_times

    def estimate_container(self, local_rq) -> int:
        """Estimates how many containers is required
        Returns:
            int: number of containers needed
        """
        return 1

    def wait_available_container(self, container_need) -> List:
        """Wait for other requests to end the container occupation

        Args:
            container_need (int): The number of containers needs to created

        Returns:
            List: Available containers
        """
        if not len(self.executing_rqs):
            print(f"No running requests")
            return []
        print(f"There are {len(self.executing_rqs)} of requests running")

        # Predict the expec_end_ts of that running requests
        exp_end_times = self.analyze_history()
        now = time.time()
        if exp_end_times:
            wait_time = max(list(map(lambda x: x-now, exp_end_times)))/1000
            # wait_time = 2
            log_id = str(uuid.uuid4())
            print(
                f"In {log_id}: We believe that wait for {wait_time} seconds to get {len(exp_end_times)} of containers")
            time.sleep(wait_time)
            print(
                f"In {log_id}: After wait {wait_time} seconds, the num of avaiable container is {len(self.container_pool)}, we expect {len(exp_end_times)} of containers")

        candidata_containers = []
        while self.container_pool:
            candidata_containers.append(self.container_pool.pop(0))
            if len(candidata_containers) == container_need:
                break

        return candidata_containers

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
            # Update core-affinity list
            core_manager.schedule_cores(container, concurrency)
            candidate_containers.append(container)
            container_created += 1

        # 2. 如果容器数量不够，则等待至容器可用
        # """
        # TODO 还需要量化的等待可用容器带来的内存开销
        # 1. 现在正在执行的请求，拥有这些请求开始的时间
        # 2. 根据历史执行时间，这些请求还有多久能释放容器
        # 3. 判断需要等待的时间，和冷启动时间比较
        # """
        # container_need = num_containers - container_created
        # if container_need != 0:
        #     print(f"Still need more {container_need} of containers in group {self.name}")
        #     avaiable_containers = self.wait_available_container(
        #         container_need=container_need)

        #     candidate_containers.extend(avaiable_containers)
        #     container_created += len(avaiable_containers)
        #     if len(avaiable_containers):
        #         print(
        #             f"We get {len(avaiable_containers)} of containers by waiting execution")

        # 3. 创建剩下所需的容器
        while container_created < num_containers:
            container = None
            while not container:
                start = time.time()
                container = self.create_container(function=function)
                cold_start = (time.time() - start) * 1000  # Coverts s to ms
                self.time_cold.append(cold_start)
                # container = self.fake_create_container(function=function)

            # Update core-affinity list
            core_manager.schedule_cores(container, concurrency)
            candidate_containers.append(container)
            container_created += 1
            logging.info(
                f"{container_created} of containers have been created")
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

            core_manager.release_busy_cores(container)
            for req in requests:
                self.record_info(req)

    def record_info(self, req):
        print(
            f"request {req.function.info.function_name} is done, recording the execution infomation...")
        self.historical_reqs.append(req)
        self.history_duration.append(req.duration)
        print(f"{req.function.info.function_name},{req.duration}",
              file=log_file, flush=True)
        if req.defer:
            self.defer_times.append(req.defer)
