package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

func sendToSFSScheduler(pid int, functionId string) {
	socket, err := net.DialUDP("udp", nil, &net.UDPAddr{
		IP:   net.IPv4(172, 17, 0, 1),
		Port: 4009,
	})
	if err != nil {
		logrus.Fatal("Failed to connect UDP server because: ", err)
	}
	defer socket.Close()
	dataMap := make(map[string]string)
	dataMap["pid"] = strconv.Itoa(pid)
	dataMap["id"] = functionId
	str, err := json.Marshal(dataMap)

	if err != nil {
		logrus.Fatal(err)
	}

	_, err = socket.Write(str) // send
	if err != nil {
		logrus.Fatal("Data send err: ", err)
		return
	}
	data := make([]byte, 4096)
	n, remoteAddr, err := socket.ReadFromUDP(data) // receive
	if err != nil {
		logrus.Fatal("Data received err: ", err)
		return
	}
	logrus.Debugf("recv:%v addr:%v count:%v\n", string(data[:n]), remoteAddr, n)
}

func execCmd(schedParams []string, functionId string, activateSFS bool) []byte {
	cmd := exec.Command(schedParams[0], schedParams[1:]...)

	// Create a standard output pipe
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		logrus.Fatal("StdoutPipe error because: ", err)
	}

	err = cmd.Start()
	if err != nil {
		logrus.Fatal("Command ", schedParams, " start gets error because: ", err)
	}
	if activateSFS {
		logrus.Info("Sending pid: ", cmd.Process.Pid, "to SFS scheduler")
		sendToSFSScheduler(cmd.Process.Pid, functionId)
	}

	// Read result in the output pipe
	out := make([]byte, 1024)
	length, err := stdout.Read(out)
	if err != nil {
		logrus.Fatal("Read result in stdout error because: ", err)
	}

	err = cmd.Wait()
	if err != nil {
		logrus.Fatal("Command ", schedParams, " wait gets error because: ", err)
	}
	return out[:length]
}

func invokeFunction(req map[string]interface{}) map[string]interface{} {
	// Invokes the function
	functionId, _ := req["function_id"].(string)

	// Extract boto3 parameters
	azureData, ok := req["azure_data"].(map[string]interface{})
	if !ok {
		logrus.Fatal("azure_data not found or not a map")
		return nil
	}

	awsBoto3, ok := azureData["aws_boto3"].(map[string]interface{})
	if !ok {
		logrus.Fatal("aws_boto3 not found or not a map")
		return nil
	}

	serviceName := "s3"
	accessKeyID := awsBoto3["aws_access_key_id"].(string)
	secretAccessKey := awsBoto3["aws_secret_access_key"].(string)
	regionName := awsBoto3["region_name"].(string)
	concurrency := req["concurrency"].(int)
	var activateSFS bool
	if activate, ok := azureData["activate_SFS"].(bool); ok {
		activateSFS = activate
	}

	// Prepare command parameters
	schedParams := []string{"./function_exec", serviceName, accessKeyID, secretAccessKey, regionName, strconv.Itoa(concurrency)}

	// Call execCmd to execute the command
	out := execCmd(schedParams, functionId, activateSFS)

	var result map[string]interface{}
	err := json.Unmarshal(out, &result)
	if err != nil {
		logrus.Fatal("Failed because: ", err)
	}
	// responses[functionId] = result
	return result
}

func batchRun(c *gin.Context) {
	reqs := make([]map[string]interface{}, 0)
	c.BindJSON(&reqs)
	logrus.Debug("req: ", reqs)

	responses := make(map[string]interface{}, len(reqs))
	logrus.Debug("len of reqs", len(reqs))
	for i := range reqs {
		reqs[i]["concurrency"] = len(reqs)
	}

	startTime := time.Now()
	logrus.Debug("Start at. ..", startTime)

	for _, req := range reqs {
		queueTime := float64(time.Since(startTime).Seconds()) * 1000
		result := invokeFunction(req)
		result["queue_time"] = queueTime
		functionID, ok := req["function_id"].(string)
		if !ok {
			logrus.Error("function_id not found or not a string")
			continue
		}
		responses[functionID] = result
	}

	logrus.Debug("responses: ", responses)
	c.JSON(http.StatusOK, responses)
}

func stats(c *gin.Context) {
	response := make(map[string]string)
	response["workdir"], _ = os.Getwd()
	c.JSON(http.StatusOK, response)
}

func initFunc(c *gin.Context) {
	c.JSON(http.StatusOK, "OK")
}

func main() {
	logrus.SetLevel(logrus.InfoLevel)

	route := gin.Default()
	route.POST("/batch_run", batchRun)
	route.GET("/status", stats)
	route.POST("/init", initFunc)
	add := fmt.Sprintf(":%s", PROXY)
	route.Run(add)

}
