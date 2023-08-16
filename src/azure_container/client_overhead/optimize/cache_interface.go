package main

type CacheStrategy interface {
	Get(key string) (interface{}, bool)
	Set(key string, value interface{})
	ShouldEvict() bool
	Evict()
	Keys() []string
}
