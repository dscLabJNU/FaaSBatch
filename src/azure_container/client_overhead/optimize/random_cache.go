package main

import (
	"math/rand"

	"github.com/sirupsen/logrus"
)

type RandomCache struct {
	capacity   int
	cache      map[string]interface{}
	keys       []string
	numOfEvict int
}

func NewRandomCache(capacity int) *RandomCache {
	return &RandomCache{
		capacity: capacity,
		cache:    make(map[string]interface{}),
	}
}

func (c *RandomCache) Get(key string) (interface{}, bool) {
	logrus.Info("Getting key by RandomCache")
	value, found := c.cache[key]
	return value, found
}

func (c *RandomCache) Set(key string, value interface{}, addParams map[string]interface{}) {
	logrus.Info("Setting key by RandomCache")
	c.cache[key] = value
	c.keys = append(c.keys, key)
	if c.ShouldEvict() {
		c.Evict()
	}
}

func (c *RandomCache) ShouldEvict() bool {
	return len(c.keys) > c.capacity
}

func (c *RandomCache) Evict() {
	randomIndex := rand.Intn(len(c.keys))
	delete(c.cache, c.keys[randomIndex])
	c.keys = append(c.keys[:randomIndex], c.keys[randomIndex+1:]...)
	c.numOfEvict++
}

func (c *RandomCache) Keys() []string {
	return c.keys
}

func (c *RandomCache) numOfEviction() int {
	return c.numOfEvict
}
