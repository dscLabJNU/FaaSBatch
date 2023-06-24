import const
import logging
import random
from collections import defaultdict
import sys
import time
logger = logging.getLogger(__name__)


class EvictionStrategy:
    def __init__(self, maxlen=None):
        if maxlen is None:  # 如果在子类中没有提供 maxlen，就赋予默认值
            self.maxlen = const.DEFAULT_CACHE_MAXLEN
        else:
            self.maxlen = maxlen
        logger.info(
            f"Using {self.__class__.__name__}(maxlen={self.maxlen}) as eviction strategy")

    def should_evict(self, cache):
        return len(cache.pool) >= self.maxlen

    def update(self, key, cache):
        pass

    def evict(self, cache, keys_to_evict):
        raise NotImplementedError


class Random(EvictionStrategy):
    def __init__(self, maxlen=None):
        super().__init__(maxlen)

    def evict(self, cache, keys_to_evict):
        random_key = random.choice(list(cache.pool.keys()))
        del cache.pool[random_key]
        logger.info(f"Evicting random cache item with key: [{random_key}]")


class GDSF(EvictionStrategy):
    """
    Evication policy used in FaaSCache (ASPLOS '21)
    """

    def __init__(self, maxlen=None):
        super().__init__(maxlen)
        self.priority = dict()
        # Creation time cost for each instance
        self.cost = defaultdict(lambda: 0)
        # Logical clock for each instance
        self.clock = defaultdict(lambda: 0)
        # Memory occupation for each instance
        self.size = defaultdict(lambda: 0)

    def should_evict(self, cache):
        return super().should_evict(cache=cache)

    def update(self, key, cache):
        self.calculate_priority(cache)

    def calculate_priority(self, cache):
        logger.info(f"Updating the priority of cache objects")
        # create a copy to avoid mutated during iteration
        for key, instance in list(cache.pool.items()):
            freq = cache.frequency[key]
            clock = self.clock[key]
            cost = instance.get("creation_time")  # in second
            size = sys.getsizeof(instance)  # in bytes
            prio = clock + (freq * cost)/size
            self.priority[key] = prio
            logger.info(
                f"freq: {freq}, clock: {clock}, cost: {cost}, size: {size}, prio: {prio}")

    def evict(self, cache, keys_to_evict):
        self.calculate_priority(cache)

        min_priority_key = min(self.priority, key=self.priority.get)
        # update clock
        self.clock[min_priority_key] = self.priority[min_priority_key]
        logger.info(f"Evicting LFU cache with key: [{min_priority_key}]")

        if min_priority_key in cache.pool:
            del cache.pool[min_priority_key]
        if min_priority_key in cache.hits:
            del cache.hits[min_priority_key]
        if min_priority_key in self.priority:
            del self.priority[min_priority_key]


class LRU(EvictionStrategy):
    def __init__(self, maxlen=None):
        super().__init__(maxlen)

    def update(self, key, cache):
        """
        Remove existing key and reinsert it to update it as the most recently used.
        """
        value = cache.pool.pop(key)
        cache.pool[key] = value

    def evict(self, cache, keys_to_evict):
        logger.info(f"Evicting LRU cache [{cache}]")
        cache.pool.popitem(last=False)


class LFU(EvictionStrategy):
    def __init__(self, maxlen=None):
        super().__init__(maxlen)
        self.priority = dict()

    def should_evict(self, cache):
        return super().should_evict(cache=cache)

    def calculate_priority(self, cache):
        logger.info(f"Updating the priority of cache objects")
        for key in cache.pool.keys():
            self.priority[key] = cache.hits[key]

    def evict(self, cache, keys_to_evict):
        self.calculate_priority(cache)
        # 找出优先级最低的键
        min_priority_key = min(self.priority, key=self.priority.get)

        logger.info(f"Evicting LFU cache with key: [{min_priority_key}]")
        del cache.pool[min_priority_key]
        del cache.hits[min_priority_key]
        del self.priority[min_priority_key]


class MyCache(EvictionStrategy):
    def __init__(self, maxlen=None):
        super().__init__(maxlen)
        self.minlen = self.maxlen
        self.keys_to_evict = []

    def should_evict(self, cache):
        """
        Check if any keys in the cache should be evicted based on their idle time
        """
        logger.info(f"Cache req_iat: {dict(cache.req_iat)}")
        keys_to_evict = []
        num_cache_items = len(cache.pool)

        if num_cache_items <= self.minlen:
            # Number of cached items are not reach the lower limit yet
            return keys_to_evict

        for key, iat_sequence in cache.req_iat.items():
            # iat_sequence.get_last() -> timestamp the last request arrived
            idle_time = time.time() - iat_sequence.get_last()
            logger.info(f"Key [{key}] has been idle for {idle_time} seconds")

            if idle_time > iat_sequence.get_percentail(
                    percent=const.DEFAULT_IDEAL_PERCENTAIL) * 3:
                if key in cache.pool:
                    """
                    A key value that exists in ${cache_req_iat} 
                    does not necessarily also exist in ${cache.pool}
                    """
                    logger.info(f"Adding key [{key}] to eviction list...")
                    # Make sure the number of items in cache pool always >= self.minlen
                    if num_cache_items - len(keys_to_evict) <= self.minlen:
                        logger.info(
                            f"Reach the min len [{self.minlen}] of the cache")
                        break
                    keys_to_evict.append(key)

        return keys_to_evict

    def evict(self, cache, keys_to_evict):
        logger.info(
            f"Ready evicting keys: {keys_to_evict}, number of cache is: {len(cache.pool)}")
        for i, evict_key in enumerate(keys_to_evict):
            # Usuing LRU as the eviction strategy
            k_v_tuple = cache.pool.popitem(last=False)
            evict_key = k_v_tuple[0]
            logger.info(f"Evicting MyCache cache with key: [{evict_key}]")
            if evict_key in cache.hits:
                del cache.hits[evict_key]
            if evict_key in cache.req_iat:
                del cache.req_iat[evict_key]


class InfiniteCache(EvictionStrategy):
    """
    Cacheing all instances into memory
    """

    def __init__(self, maxlen=9999999):
        super().__init__(maxlen)

    def should_evict(self, cache):
        return False

    def evict(self, cache, keys_to_evict):
        pass
