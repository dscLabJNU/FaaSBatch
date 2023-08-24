package main

import (
	"github.com/sirupsen/logrus"
)

type LFUCache struct {
	capacity   int
	cache      map[string]interface{}
	freqMap    map[string]int
	numOfEvict int
}

func NewLFUCache(capacity int) *LFUCache {
	return &LFUCache{
		capacity: capacity,
		cache:    make(map[string]interface{}),
		freqMap:  make(map[string]int),
	}
}

func (c *LFUCache) Get(key string) (interface{}, bool) {
	logrus.Info("Getting key by LFUCache")
	value, found := c.cache[key]
	if found {
		c.freqMap[key]++
	}
	return value, found
}

func (c *LFUCache) Set(key string, value interface{}, addParams map[string]interface{}) {
	logrus.Info("Setting key by LFUCache")
	c.cache[key] = value
	c.freqMap[key]++
	if c.ShouldEvict() {
		c.Evict()
	}
}

func (c *LFUCache) ShouldEvict() bool {
	return len(c.cache) > c.capacity
}

func (c *LFUCache) Evict() {
	minFreq := int(^uint(0) >> 1)
	minKey := ""
	for k, freq := range c.freqMap {
		if freq < minFreq {
			minFreq = freq
			minKey = k
		}
	}
	delete(c.cache, minKey)
	delete(c.freqMap, minKey)
	c.numOfEvict++
}

func (c *LFUCache) Keys() []string {
	keys := make([]string, 0, len(c.cache))
	for key := range c.cache {
		keys = append(keys, key)
	}
	return keys
}

func (c *LFUCache) numOfEviction() int {
	return c.numOfEvict
}
