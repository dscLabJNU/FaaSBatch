package main

func getCoresList(cpuMask int) []int {
	var cores []int
	index := 0

	for cpuMask != 0 {
		if cpuMask&1 != 0 {
			cores = append(cores, index)
		}
		index++
		cpuMask >>= 1
	}
	return cores
}
