package main

import (
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/gin-gonic/gin"
)

func parallel_exe(req map[string]string, wg *sync.WaitGroup, responses map[string]interface{}) {
	// 计数器减一
	defer wg.Done()
	responses[req["function_id"]] = run_main()
}

func run(c *gin.Context) {
	reqs := make([]map[string]string, 0)
	c.BindJSON(&reqs)

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
	route.POST("/batch_run", run)
	route.GET("/status", stats)
	route.POST("/init", init_func)

	// Listen and Server in 0.0.0.0:5000
	route.Run(":5000")
}
