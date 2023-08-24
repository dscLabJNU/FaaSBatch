package main

import (
	"container/list"

	"github.com/sirupsen/logrus"
)

type LRUCache struct {
	capacity   int
	cache      map[string]*list.Element
	items      *list.List
	numOfEvict int
}

func NewLRUCache(capacity int) *LRUCache {
	return &LRUCache{
		capacity: capacity,
		cache:    make(map[string]*list.Element),
		items:    list.New(),
	}
}

func (c *LRUCache) Get(key string) (interface{}, bool) {
	logrus.Info("Getting key by LRU")
	if item, found := c.cache[key]; found {
		c.items.MoveToFront(item)
		return item.Value.(*entry).value, true
	}
	return nil, false
}

func (c *LRUCache) Set(key string, value interface{}, addParams map[string]interface{}) {
	logrus.Info("Setting key by LRU")
	if item, found := c.cache[key]; found {
		c.items.MoveToFront(item)
		item.Value.(*entry).value = value
		return
	}
	item := c.items.PushFront(&entry{key, value})
	c.cache[key] = item
	if c.ShouldEvict() {
		c.Evict()
	}
}

func (c *LRUCache) ShouldEvict() bool {
	return c.items.Len() > c.capacity
}

func (c *LRUCache) Evict() {
	c.numOfEvict++
	item := c.items.Back()
	if item != nil {
		c.InnerRemove(item.Value.(*entry).key)
	}
}

func (c *LRUCache) numOfEviction() int {
	return c.numOfEvict
}

func (c *LRUCache) InnerRemove(key string) {
	if item, found := c.cache[key]; found {
		c.items.Remove(item)
		delete(c.cache, key)
	}
}

func (c *LRUCache) Keys() []string {
	keys := make([]string, 0, len(c.cache))
	for key := range c.cache {
		keys = append(keys, key)
	}
	return keys
}
