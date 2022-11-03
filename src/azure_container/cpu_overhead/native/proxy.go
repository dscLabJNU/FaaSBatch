package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

type FibResult struct {
	StartTime float64 `json:"start_time"`
	ExecTime  float64 `json:"exec_time"`
	EndTime   float64 `json:"end_time"`
	Result    int     `json:"result"`
	QueueTime int64   `json:"queue_time"`
}

func sendToSFSScheduler(pid int, functionId string) {
	socket, err := net.DialUDP("udp", nil, &net.UDPAddr{
		IP:   net.IPv4(172, 18, 0, 1),
		Port: 4009,
	})
	if err != nil {
		log.Fatal("Failed to connect UDP server because: ", err)
	}
	defer socket.Close()
	dataMap := make(map[string]string)
	dataMap["pid"] = strconv.Itoa(pid)
	dataMap["id"] = functionId
	str, err := json.Marshal(dataMap)

	if err != nil {
		fmt.Println(err)
	}

	_, err = socket.Write(str) // send
	if err != nil {
		fmt.Println("Data send err: ", err)
		return
	}
	data := make([]byte, 4096)
	n, remoteAddr, err := socket.ReadFromUDP(data) // receive
	if err != nil {
		fmt.Println("Data received err: ", err)
		return
	}
	fmt.Printf("recv:%v addr:%v count:%v\n", string(data[:n]), remoteAddr, n)
}

func execCmd(schedParams []string, functionId string, activateSFS bool) []byte {
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
	if activateSFS {
		log.Println("Sending pid: ", cmd.Process.Pid, "to SFS sheduler")
		sendToSFSScheduler(cmd.Process.Pid, functionId)
	}

	// Read result in the ouput pipe
	out := make([]byte, 1024)
	length, err := stdout.Read(out)
	if err != nil {
		log.Fatal("Read result in stdout error because: ", err)
	}

	err = cmd.Wait()
	if err != nil {
		log.Fatal("Command ", schedParams, " wait gets error because: ", err)
	}
	return out[:length]
}

func invokeFunction(req map[string]interface{}, responses map[string]interface{}) string {
	// Invokes the batched functions one by one
	functionId, _ := req["function_id"].(string)

	var schedParams = []string{"python3", "fib.py"}
	var activateSFS bool
	if entry, ok := req["azure_data"].(map[string]interface{}); ok {
		inputN := strconv.Itoa(int(entry["input_n"].(float64)))
		schedParams = append(schedParams, inputN)
		activateSFS = entry["activate_SFS"].(bool)
		log.Println("Actvated SFS scheduling: ", activateSFS)
		// log.Printf("Runing python fip.py %s\n", inputN)
	}
	log.Println("cmdParams:", schedParams)

	out := execCmd(schedParams, functionId, activateSFS)

	var fibResult FibResult
	err := json.Unmarshal(out, &fibResult)
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
		log.Println("req: ", req)
		queueTime := time.Since(startTime).Milliseconds()
		functionId := invokeFunction(req, responses)

		if entry, ok := responses[functionId].(FibResult); ok {
			// Modify the copy
			entry.QueueTime = queueTime
			// Reassign map entry
			responses[functionId] = entry
		}
		log.Println("Funciton", functionId, "has been waited for", queueTime, "ms")
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
