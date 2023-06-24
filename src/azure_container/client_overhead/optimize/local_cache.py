import time
from history_record import HistoryRecord
import collections
from eviction_strategy import LRU
import logging
import psutil
import os
logger = logging.getLogger(__name__)


class LocalCache():
    notFound = object()

    def __init__(self, eviction_strategy=None):
        if eviction_strategy is None:
            eviction_strategy = LRU()
        self.pool = collections.OrderedDict()
        self.hits = collections.Counter()
        self.frequency = collections.Counter()
        self.eviction_strategy = eviction_strategy
        self.init_mem_util = self.get_cur_mem_util()

        # IaT of each request
        self.req_iat = collections.defaultdict(lambda: HistoryRecord())

    def get_cur_mem_util(self):
        # in MB
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024 / 8

    def cache_info(self):
        try:
            total_hits = sum(self.hits.values())
            total_invos = sum(self.frequency.values())
            logger.info(f"Getting hit rate... [{total_hits}/{total_invos}]")
            hit_rate = total_hits / total_invos
            memory_used = self.get_cur_mem_util() - self.init_mem_util
            return {"hits": total_hits, "invos": total_invos, 
                    "hit_rate": hit_rate, "memory_used": memory_used}
        except ZeroDivisionError:
            logger.error("Error: No requests received yet, division by zero, ")
            return {"hits": 0, "invos": 0, "hit_rate": 0, "memory_used": self.init_mem_util}

    def update(self, key):
        self.eviction_strategy.update(key=key, cache=self)

    def get(self, key):
        # Request arrived
        now_time = time.time()
        self.req_iat[key].append(now_time)
        # logger.info(f"key: {key} => IaT: {list(self.req_iat[key].values)}")
        # logger.info(f"iat 95 tail: {self.req_iat[key].get_percentail(percent=95)}")

        self.frequency[key] += 1
        value = self.pool.get(key, self.notFound)
        if value is not self.notFound:
            logger.info(f"key [{key}] hit! [{value}]")
            self.hits[key] += 1  # 更新访问计数器
            self.update(key=key)
            logger.debug(f"Cache hits: {self.hits}")
            return value
        else:
            logger.info(f"Cache miss [{key}], execute in a normal way")
            return self.notFound

    def set(self, key, value):
        if key in self.pool:
            logger.debug("This k-v piar has already existed in cache")
            return

        keys_to_evict = self.eviction_strategy.should_evict(self)
        if keys_to_evict:
            self.eviction_strategy.evict(self, keys_to_evict)

        logger.info(f"Setting cache with key [{key}] and value [{value}]")
        self.hits[key] += 1  # 更新访问计数器
        self.pool[key] = value
