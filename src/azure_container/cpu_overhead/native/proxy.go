package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

type FibResult struct {
	StartTime float64 `json:"start_time"`
	Duration  float64 `json:"duration"`
	EndTime   float64 `json:"end_time"`
	Result    int     `json:"result"`
	WaitTime  int64   `json:"wait_time"`
}

func invokeFunction(req map[string]interface{}, responses map[string]interface{}) string {
	functionId, _ := req["function_id"].(string)

	var schedParams = []string{"python3", "fib.py"}
	if entry, ok := req["azure_data"].(map[string]interface{}); ok {
		inputN := strconv.Itoa(int(entry["input_n"].(float64)))
		schedParams = append(schedParams, inputN)
		// log.Printf("Runing python fip.py %s\n", inputN)
	}
	log.Println("cmdParams:", schedParams)

	cmd := exec.Command("sudo", schedParams...)
	out, err := cmd.Output()
	if err != nil {
		log.Fatal(err)
	}

	var fibResult FibResult
	err = json.Unmarshal(out, &fibResult)
	if err != nil {
		log.Println("Failed because: ", err)
	}
	responses[functionId] = fibResult
	return functionId
}

// This function recieves one request each time
func run(c *gin.Context) {
	req := make(map[string]interface{}, 1)
	c.BindJSON(&req)
	log.Println("req: ", req)
	responses := make(map[string]interface{}, 1)

	function_id, _ := req["function_id"].(string)

	responses[function_id] = run_main()
	c.JSON(http.StatusOK, responses)
}

// This function recieves serverl requests each time, but executes in blocking
func batch_run(c *gin.Context) {
	reqs := make([]map[string]interface{}, 0)
	c.BindJSON(&reqs)
	log.Print("len of reqs: ", len(reqs))
	responses := make(map[string]interface{})
	startTime := time.Now()
	for _, req := range reqs {
		functionId := invokeFunction(req, responses)
		waitTime := time.Since(startTime)

		if entry, ok := responses[functionId].(FibResult); ok {
			// Modify the copy
			entry.WaitTime = waitTime.Milliseconds()
			// Reassign map entry
			responses[functionId] = entry
		}
		log.Println("Funciton", functionId, "has been waited for", waitTime)
		log.Println("response:", responses[functionId])
	}

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
}
