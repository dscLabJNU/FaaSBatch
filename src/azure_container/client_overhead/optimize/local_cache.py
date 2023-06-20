import time
from history_record import HistoryRecord
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
        self.frequency = collections.Counter()
        self.eviction_strategy = eviction_strategy

        # IaT of each request
        self.req_iat = collections.defaultdict(lambda : HistoryRecord())

    def cache_info(self):
        try:
            total_hits = sum(self.hits.values())
            total_invos = sum(self.frequency.values())
            logger.info(f"Getting hit rate... [{total_hits}/{total_invos}]")
            hit_rate = total_hits / total_invos
            return {"hits": total_hits, "invos": total_invos, "hit_rate": hit_rate}
        except ZeroDivisionError:
            logger.error("Error: No requests received yet, division by zero, ")
            return {"hits": 0, "invos": 0, "hit_rate": 0}

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
        if self.eviction_strategy.should_evict(self):
            logger.info(
                f"Cache pool is full, limit in {self.eviction_strategy.maxlen}")
            self.eviction_strategy.evict(self)

        logger.info(f"Setting cache with key [{key}] and value [{value}]")
        self.hits[key] += 1  # 更新访问计数器
        self.pool[key] = value
