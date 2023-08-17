package main

type CacheStrategy interface {
	Get(key string) (interface{}, bool)
	Set(key string, value interface{}, addParams map[string]interface{})
	ShouldEvict() bool
	Evict()
	Keys() []string
}
