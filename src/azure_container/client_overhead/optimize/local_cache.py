import time
import collections
from eviction_strategy import LRU
import logging
logger = logging.getLogger(__name__)


class LocalCache():
    notFound = object()

    def __init__(self, eviction_strategy=None):
        if eviction_strategy is None:
            eviction_strategy = LRU()
        self.pool = collections.OrderedDict()
        self.hits = collections.Counter()
        self.num_invos = 0
        self.eviction_strategy = eviction_strategy

    def get_hit_rate(self):
        try:
            total_hits = sum(self.hits.values())
            return total_hits / self.num_invos
        except ZeroDivisionError:
            logger.error("Error: No requests received yet, division by zero, ")
            return 0

    @staticmethod
    def nowTime():
        return int(time.time())

    def update(self, key):
        self.eviction_strategy.update(key=key, cache=self)

    def get(self, key):
        self.num_invos += 1
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
        if self.eviction_strategy.should_evict(self):
            logger.info(
                f"Cache pool is full, limit in {self.eviction_strategy.maxlen}")
            self.eviction_strategy.evict(self)

        logger.info(f"Setting cache with key [{key}] and value [{value}]")
        self.hits[key] += 1  # 更新访问计数器
        self.pool[key] = value
