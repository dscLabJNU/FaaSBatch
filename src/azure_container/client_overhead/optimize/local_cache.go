package main

import (
	"sync"

	"github.com/sirupsen/logrus"
)

type LocalCache struct {
	cache           CacheStrategy
	keyHits         map[string]int
	keyRequests     map[string]int
	mu              sync.Mutex
	totalCachedKeys int
}
type entry struct {
	key   string
	value interface{}
}

func (lc *LocalCache) getTotalCachedKeys() map[string]interface{} {
	info := make(map[string]interface{})
	info["total_cached_keys"] = lc.totalCachedKeys
	return info
}

func (lc *LocalCache) cacheInfo() map[string]interface{} {
	info := make(map[string]interface{})

	// 保存每个键的详细信息，包括命中次数、总访问次数和命中率
	keyDetails := make(map[string]map[string]interface{})
	for key, hits := range lc.keyHits {
		requests := lc.keyRequests[key]
		details := make(map[string]interface{})
		details["hits"] = hits
		details["invos"] = requests
		if requests > 0 {
			details["hit_rate"] = float64(hits) / float64(requests)
		} else {
			details["hit_rate"] = 0
		}
		keyDetails[key] = details
	}
	info["key_cache_details"] = keyDetails

	return info
}

func NewLocalCache(algorithm string, capacity int) *LocalCache {
	var cache CacheStrategy

	switch algorithm {
	case "LRU":
		cache = NewLRU(capacity)
	case "Unbounded":
		cache = NewUnboundedCache()
	case "GDSF":
		cache = NewGDSF(capacity)
	default:
		logrus.Error("Unknown cache algorithm:", algorithm)
	}

	localCache := &LocalCache{
		cache:       cache,
		keyHits:     make(map[string]int),
		keyRequests: make(map[string]int),
	}

	logrus.Infof("Cache strategy set to [%s] with a capacity of [%d]\n", algorithm, capacity)

	return localCache
}

func (lc *LocalCache) Get(key string) (interface{}, bool) {
	lc.mu.Lock()
	defer lc.mu.Unlock()
	lc.keyRequests[key]++
	value, found := lc.cache.Get(key)
	if found {
		lc.keyHits[key]++
	}
	return value, found
}

func (lc *LocalCache) Set(key string, value interface{}, addParams map[string]interface{}) {
	lc.mu.Lock()
	defer lc.mu.Unlock()
	lc.cache.Set(key, value, addParams)
	lc.totalCachedKeys++
	logrus.Infof("S3 client key: [%s] created and added to cache", key)
	lc.PrintKeys()
}

func (lc *LocalCache) PrintKeys() {
	keys := lc.cache.Keys()
	logrus.Info("Cache keys:", keys)
}
