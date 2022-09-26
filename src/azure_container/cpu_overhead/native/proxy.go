package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
)

func batch_run(c *gin.Context) {
	reqs := make([]map[string]string, 0)
	c.BindJSON(&reqs)
	log.Print("len of reqs: ", len(reqs))
	responses := make(map[string]interface{})
	for _, req := range reqs {
		responses[req["function_id"]] = run_main()
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
	route.POST("/batch_run", batch_run)
	route.GET("/status", stats)
	route.POST("/init", init_func)

	// Listen and Server in 0.0.0.0:5000
	route.Run(":5000")
}
