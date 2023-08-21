from abc import ABC, abstractmethod
from collections import deque, defaultdict
from enum import Enum
import numpy as np
import random


class StrategyType(Enum):
    SlidingWindow = "SlidingWindow"
    EMA = "EMA"


class RequestRecorder:
    def __init__(self, init_info):
        self.strategy = self._create_strategy(init_info)

    def _create_strategy(self, init_info):
        strategy = init_info.get("identify_strategy", None)
        if not strategy:
            raise ValueError("Please indicate identify strategy!")
        elif strategy == StrategyType.EMA:
            return EMA(init_info['hot_percentail'])
        # 其他策略可以在这里添加
        else:
            raise ValueError("Indicating a unimplemented strategy...")

    def add_request(self, key, arrival_time):
        self.strategy.add_request(key, arrival_time)

    def is_hot(self, key):
        return self.strategy.is_hot(key)

    def get_popular_reqs(self):
        return self.strategy.get_popular_reqs()


class RequestStrategy(ABC):
    def __init__(self):
        self.last_access_times = defaultdict(float)
        self.iat_estimates = defaultdict(float)

    @abstractmethod
    def add_request(self, key, arrival_time):
        pass

    @abstractmethod
    def is_hot(self, key):
        pass

    @abstractmethod
    def get_popular_reqs(self, local_rq):
        pass


class EMA(RequestStrategy):
    def __init__(self, hot_percentile=20, alpha=0.1, sampling_ratio=0.6):
        super().__init__()
        self.hot_percentile = hot_percentile
        self.alpha = alpha
        self.sampling_ratio = sampling_ratio

    def add_request(self, key, arrival_time):
        # Sampling in a specific possibility
        # if random.random() < self.sampling_ratio:
        last_access_time = self.last_access_times.get(key, arrival_time)
        current_iat = arrival_time - last_access_time
        iat_estimate = self.iat_estimates.get(key, current_iat)

        # 计算指数平均IAT
        iat_estimate = self.alpha * iat_estimate + \
            (1 - self.alpha) * current_iat

        self.iat_estimates[key] = iat_estimate
        self.last_access_times[key] = arrival_time  # 更新最后访问时间

    def is_hot(self, key):
        # 这个方法可以根据需要实现，例如通过比较某个键的IAT与阈值
        pass

    # def get_popular_reqs(self):
    #     iat_values = list(self.iat_estimates.values())
    #     iat_threshold = np.percentile(iat_values, self.hot_percentile)
    #     popular_reqs = [key for key, iat_estimate in self.iat_estimates.items(
    #     ) if iat_estimate < iat_threshold]
    #     return set(popular_reqs)

    def get_popular_reqs(self):
        iat_values = [v for v in self.iat_estimates.values() if v >
                      0]  # 过滤 IAT 为 0 的值
        iat_threshold = np.percentile(iat_values, self.hot_percentile)
        popular_reqs = [key for key, iat_estimate in self.iat_estimates.items(
        ) if iat_estimate > 0 and iat_estimate < iat_threshold]
        return set(popular_reqs)


if __name__ == "__main__":
    # 设置随机种子，确保可重复性
    np.random.seed(42)
    random.seed(42)

    # 生成Zipf分布的请求数据
    num_requests = 10000
    num_keys = 100
    keys = [f'Key-{i}' for i in range(num_keys)]
    zipf_distribution = np.random.zipf(1.5, num_requests)
    # 限制范围
    zipf_distribution = zipf_distribution[zipf_distribution <= num_keys]
    local_rq = [{'key': keys[i - 1], 'arrival_time': t}
                for i, t in zip(zipf_distribution, range(num_requests))]
    # 初始化 RequestRecorder 类，并选择EMA策略
    init_info = {
        'identify_strategy': StrategyType.EMA,
        'hot_percentail': 10,
    }

    recorder = RequestRecorder(init_info)

    # 将请求数据添加到 recorder
    for req in local_rq:
        recorder.add_request(req['key'], req['arrival_time'])

    # 获取热门请求
    popular_reqs = recorder.get_popular_reqs()
    print("Popular requests:", popular_reqs)
    data = recorder.strategy.iat_estimates
    # sorted_data = {k: v for k, v in sorted(data.items(), key=lambda item: item[1]) if v != 0}
    # print(sorted_data)

    # 预测结果并断言
    expected_popular_reqs = set(['Key-1', 'Key-22', 'Key-31', 'Key-2', 'Key-4',
                                'Key-7', 'Key-0', 'Key-3', 'Key-6', 'Key-13'])  # 预测'Key-0'是热门键
    assert popular_reqs == expected_popular_reqs, f"Expected {expected_popular_reqs}, but got {popular_reqs}"
