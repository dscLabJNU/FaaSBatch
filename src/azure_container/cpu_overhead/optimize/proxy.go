package main

import (
	"encoding/json"
	"log"
	"math/big"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"io/ioutil"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
)

type FibResult struct {
	StartTime float64 `json:"start_time"`
	ExecTime  float64 `json:"exec_time"`
	EndTime   float64 `json:"end_time"`
	Result    int     `json:"result"`
	CoreNum   string  `json:"core_num"`
}

func parallel_exe(req map[string]interface{}, wg *sync.WaitGroup, responses map[string]interface{}, core string) {
	// 计数器减一
	defer wg.Done()
	functionId, _ := req["function_id"].(string)

	// var schedParams = []string{"schedtool", "-N", "-a", core, "-e", "python3", "fib.py"}
	var schedParams = []string{ "python3", "fib.py"}
	// var schedParams = []string{"schedtool", "-F", "-p", "20", "-a", core, "-e", "python3", "fib.py"}
	if entry, ok := req["azure_data"].(map[string]interface{}); ok {
		inputN := strconv.Itoa(int(entry["input_n"].(float64)))
		schedParams = append(schedParams, inputN)
		// log.Printf("Runing python fip.py [%s] with schedtool in core %s \n", inputN, core)
	}
	log.Println("cmdParams:", schedParams)

	// 指定 core 运行 python fib.py str(inpuN)
	cmd := exec.Command("sudo", schedParams...)

	// Create a standar output pipe
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		log.Fatal("StdoutPipe error because: ", err)
	}

	err = cmd.Start()
	if err != nil {
		log.Fatal("Command ", schedParams, " start gets error because: ", err)
	}

	pid := cmd.Process.Pid
	log.Printf("Process with PID %d started\n", pid)

	// Read result in the ouput pipe
	out, _ := ioutil.ReadAll(stdout)
	err = cmd.Wait()
	if err != nil {
		log.Fatal("Command ", schedParams, " wait gets error because: ", err)
	}

	var fibResult FibResult
	err = json.Unmarshal(out, &fibResult)
	if err != nil {
		log.Println("Failed because: ", err)
	}
	fibResult.CoreNum = core
	responses[functionId] = fibResult
}

func transferCoresInfo() []int {
	pid := os.Getpid()
	log.Println("Current pid:", pid)
	cmd := exec.Command("taskset", "-p", strconv.Itoa(pid))

	out, err := cmd.Output()
	if err != nil {
		panic(err)
	}
	// log.Println("string(out): ", string(out))
	outputSlice := strings.Split(string(out), ":")
	// log.Println("outputSlice: ", outputSlice)
	oxStr := strings.TrimSpace(outputSlice[len(outputSlice)-1])
	cpuMask := new(big.Int)
	cpuMask.SetString(oxStr, 16)

	coreList := getCoresList(int(cpuMask.Int64()))
	// log.Println("Avaiable cores: ", runtime.NumCPU())
	return coreList
}

// This function executes serveral requests each time, in diffrerent threads
func batch_run(c *gin.Context) {
	reqs := make([]map[string]interface{}, 0)
	c.BindJSON(&reqs)
	log.Println("req: ", reqs)

	// Aggreated results
	responses := make(map[string]interface{}, len(reqs))
	log.Println("len of reqs", len(reqs))

	wg := &sync.WaitGroup{}

	coreList := transferCoresInfo()
	log.Println("coreList:", coreList)
	for i, req := range reqs {
		core := strconv.Itoa(coreList[i%len(coreList)])
		// log.Printf("Assigning core %s to go-routine %d", core, i)
		wg.Add(1)
		go parallel_exe(req, wg, responses, core)
	}

	// 当计数器为0时, 不再阻塞
	wg.Wait()
	c.JSON(http.StatusOK, responses)
}

// This function recieves one request each time
func run(c *gin.Context) {
	req := make(map[string]interface{}, 1)
	c.BindJSON(&req)
	log.Println("req: ", req)
	responses := make(map[string]interface{}, 1)

	value, _ := req["function_id"].(string)

	responses[value] = run_main()
	c.JSON(http.StatusOK, responses)
}

func stats(c *gin.Context) {
	response := make(map[string]string)
	response["workdir"], _ = os.Getwd()
	c.JSON(http.StatusOK, response)
}

func init_func(c *gin.Context) {
	c.JSON(http.StatusOK, "OK")
}

func main() {

	route := gin.Default()
	route.POST("/run", run)
	route.POST("/batch_run", batch_run)
	route.GET("/status", stats)
	route.POST("/init", init_func)

	// Listen and Server in 0.0.0.0:5000
	route.Run(":5000")

	// oxStr := "f"
	// cpuMask := new(big.Int)
	// cpuMask.SetString(oxStr, 16)
	// coreList := getCoresList(int(cpuMask.Int64()))
	// log.Println("coreList:", coreList)
}
