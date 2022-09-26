package main

import (
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/gin-gonic/gin"
)

func parallel_exe(req map[string]interface{}, wg *sync.WaitGroup, responses map[string]interface{}) {
	// 计数器减一
	defer wg.Done()
	functionId, _ := req["function_id"].(string)
	responses[functionId] = run_main()
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

	for _, req := range reqs {
		wg.Add(1)
		go parallel_exe(req, wg, responses)
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
}
