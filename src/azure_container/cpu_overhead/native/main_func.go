package main

import (
	"time"
)

func countDown(n int) {
	for n >= 0 {
		n -= 1
	}
}

func run_main() map[string]string {
	startTime := time.Now()
	countDown(5000000000)
	elapsedTime := time.Since(startTime)
	response := map[string]string{
		"duration": elapsedTime.String(),
	}
	return response
}
