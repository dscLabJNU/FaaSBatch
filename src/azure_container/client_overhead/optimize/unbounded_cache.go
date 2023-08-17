package main

import "github.com/sirupsen/logrus"

type UnboundedCache struct {
	cache map[string]interface{}
}

func NewUnboundedCache() *UnboundedCache {
	return &UnboundedCache{
		cache: make(map[string]interface{}),
	}
}

func (c *UnboundedCache) Get(key string) (interface{}, bool) {
	logrus.Info("Getting key by UnboundedCache")
	value, found := c.cache[key]
	return value, found
}

func (c *UnboundedCache) Set(key string, value interface{}, addParams map[string]interface{}) {
	logrus.Info("Setting key by UnboundedCache")
	c.cache[key] = value
}

func (c *UnboundedCache) ShouldEvict() bool {
	return false // UnboundedCache永远不会驱逐项
}

func (c *UnboundedCache) Evict() {
	// 无需执行任何操作，因为UnboundedCache不会驱逐项
}

func (c *UnboundedCache) Keys() []string {
	keys := make([]string, 0, len(c.cache))
	for key := range c.cache {
		keys = append(keys, key)
	}
	return keys
}
