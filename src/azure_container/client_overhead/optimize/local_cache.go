package main

import (
	"github.com/sirupsen/logrus"
)

type LocalCache struct {
	cache CacheStrategy
}

func NewLocalCache(algorithm string, capacity int) *LocalCache {
	var cache CacheStrategy

	switch algorithm {
	case "LRU":
		cache = NewLRU(capacity)
	case "Unbounded":
		cache = NewUnboundedCache()
	default:
		logrus.Error("Unknown cache algorithm:", algorithm)
	}

	localCache := &LocalCache{
		cache: cache,
	}

	logrus.Infof("Cache strategy set to [%s] with a capacity of [%d]\n", algorithm, capacity)

	return localCache
}

func (lc *LocalCache) Get(key string) (interface{}, bool) {
	return lc.cache.Get(key)
}

func (lc *LocalCache) Set(key string, value interface{}) {
	lc.cache.Set(key, value)
	logrus.Infof("S3 client key: [%s] created and added to cache", key)
	lc.PrintKeys()
}

func (lc *LocalCache) PrintKeys() {
	keys := lc.cache.Keys()
	logrus.Info("Cache keys:", keys)
}
