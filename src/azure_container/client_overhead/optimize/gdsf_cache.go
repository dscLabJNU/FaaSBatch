package main

import (
	"container/list"
	"reflect"

	"github.com/sirupsen/logrus"
)

type GDSFCache struct {
	capacity  int
	cache     map[string]*list.Element
	items     *list.List
	priority  map[string]float64
	clock     map[string]float64
	cost      map[string]float64
	size      map[string]int
	frequency map[string]int
}

func NewGDSF(capacity int) *GDSFCache {
	return &GDSFCache{
		capacity:  capacity,
		cache:     make(map[string]*list.Element),
		items:     list.New(),
		priority:  make(map[string]float64),
		clock:     make(map[string]float64),
		cost:      make(map[string]float64),
		size:      make(map[string]int),
		frequency: make(map[string]int),
	}
}

func (c *GDSFCache) Get(key string) (interface{}, bool) {
	logrus.Info("Getting key by GDSF")
	if item, found := c.cache[key]; found {
		c.frequency[key]++
		c.items.MoveToFront(item)
		return item.Value.(*entry).value, true
	}
	return nil, false
}

func (c *GDSFCache) Set(key string, value interface{}, addParams map[string]interface{}) {
	logrus.Info("Setting key by GDSF")
	if item, found := c.cache[key]; found {
		c.items.MoveToFront(item)
		item.Value.(*entry).value = value
		c.frequency[key]++
		return
	}
	size := int(reflect.TypeOf(value).Size())
	item := c.items.PushFront(&entry{key, value})
	creationTimeValue, ok := addParams["creationTime"].(float64)
	if !ok {
		logrus.Error("creationTime is not of type float64")
	}
	c.cache[key] = item
	c.cost[key] = creationTimeValue
	c.size[key] = size
	c.frequency[key] = 1
	if c.ShouldEvict() {
		c.Evict()
	}
}

func (c *GDSFCache) ShouldEvict() bool {
	return c.items.Len() > c.capacity
}

func (c *GDSFCache) Evict() {
	c.CalculatePriority()
	minPriorityKey := c.MinPriorityKey()
	c.clock[minPriorityKey] = c.priority[minPriorityKey]
	logrus.Info("Evicting GDSF cache with key: ", minPriorityKey)
	c.InnerRemove(minPriorityKey)
}

func (c *GDSFCache) CalculatePriority() {
	logrus.Info("Updating the priority of cache objects")
	for key := range c.cache {
		freq := float64(c.frequency[key])
		clock := c.clock[key]
		cost := c.cost[key]
		size := float64(c.size[key])
		prio := clock + (freq*cost)/size
		c.priority[key] = prio
		logrus.Info("freq: ", freq, ", clock: ", clock, ", cost: ", cost, ", size: ", size, ", prio: ", prio)
	}
}

func (c *GDSFCache) MinPriorityKey() string {
	minPriority := float64(1<<63 - 1)
	var minKey string
	for key, priority := range c.priority {
		if priority < minPriority {
			minPriority = priority
			minKey = key
		}
	}
	return minKey
}

func (c *GDSFCache) InnerRemove(key string) {
	if item, found := c.cache[key]; found {
		c.items.Remove(item)
		delete(c.cache, key)
		delete(c.priority, key)
		delete(c.frequency, key)
	}
}

func (c *GDSFCache) Keys() []string {
	keys := make([]string, 0, len(c.cache))
	for key := range c.cache {
		keys = append(keys, key)
	}
	return keys
}
