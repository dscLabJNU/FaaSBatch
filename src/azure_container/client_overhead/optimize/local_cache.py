import time
import collections
from eviction_strategy import DequeEvictionStrategy
import logging
logger = logging.getLogger(__name__)


class LocalCache():
    notFound = object()

    def __init__(self, eviction_strategy=None):
        if eviction_strategy is None:
            eviction_strategy = DequeEvictionStrategy()
        self.pool = collections.OrderedDict()
        self.hits = collections.Counter()
        self.eviction_strategy = eviction_strategy

    @staticmethod
    def nowTime():
        return int(time.time())

    def get(self, key):
        value = self.pool.get(key, self.notFound)
        if value is not self.notFound:
            logger.info(f"key [{key}] hit! [{value}]")
            self.hits[key] += 1  # 更新访问计数器
            logger.debug(f"Cache hits: {self.hits}")
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
