import const
import logging
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

    def evict(self, cache):
        raise NotImplementedError


class DequeEvictionStrategy(EvictionStrategy):
    def __init__(self, maxlen=None):
        super().__init__(maxlen)

    def evict(self, cache):
        logger.info(f"Evicting cache {cache}")
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

    def evict(self, cache):
        self.calculate_priority(cache)
        # 找出优先级最低的键
        min_priority_key = min(self.priority, key=self.priority.get)

        logger.info(f"Evicting cache with key: [{min_priority_key}]")
        del cache.pool[min_priority_key]
        del cache.hits[min_priority_key]
        del self.priority[min_priority_key]
