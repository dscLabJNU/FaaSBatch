package main

import (
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

type Result struct {
	Concurrency int     `json:"concurrency"`
	ExecTime    float64 `json:"exec_time"`
}
type CacheConfig struct {
	CacheStrategy string `json:"cache_strategy"`
	CacheSize     int    `json:"cache_size"`
}

func parallel_exe(req map[string]interface{}, wg *sync.WaitGroup, responses map[string]interface{}) {
	defer wg.Done()

	functionId, ok := req["function_id"].(string)
	if !ok {
		logrus.Error("function_id not found or not a string")
		return
	}

	concurrencyValue, ok := req["concurrency"].(int)
	if !ok {
		logrus.Error("concurrency not found or not a int")
		return
	}

	azureData, ok := req["azure_data"].(map[string]interface{})
	if !ok {
		logrus.Error("azure_data not found or not a map")
		return
	}

	awsBoto3, ok := azureData["aws_boto3"].(map[string]interface{})
	if !ok {
		logrus.Warn("aws_boto3 not found or not a map")
		return
	}

	params := Args{
		AzureData: AzureData{
			AWSBoto3: AWSBoto3{
				ServiceName:        "s3",
				AWSAccessKeyID:     awsBoto3["aws_access_key_id"].(string),
				AWSSecretAccessKey: awsBoto3["aws_secret_access_key"].(string),
				RegionName:         awsBoto3["region_name"].(string),
			},
		},
		Concurrency: concurrencyValue,
	}

	result := function(params)
	responses[functionId] = result
}

func createS3Client(params AWSBoto3) *s3.S3 {
	logrus.Debug("Recieved AWSBoto3 Prams: ", params)
	// 将请求参数转换为JSON字符串
	paramsJSON, err := json.Marshal(params)
	if err != nil {
		logrus.Error("Failed to hash parameters:", err)
	}

	// 使用SHA-256哈希算法计算键
	hasher := sha1.New()
	hasher.Write(paramsJSON)
	key := hex.EncodeToString(hasher.Sum(nil))
	start := time.Now()
	// 尝试从缓存中获取s3Client
	if cachedClient, found := localCache.Get(key); found {
		if s3Client, ok := cachedClient.(*s3.S3); ok {
			logrus.Info("Found key:", key, " in cache")
			return s3Client
		}
	}

	logrus.Info("Unfound key:", key, " in cache")

	// 如果未在缓存中找到，则创建新的s3Client
	creds := credentials.NewStaticCredentials(params.AWSAccessKeyID, params.AWSSecretAccessKey, "")
	config := &aws.Config{
		Region:      aws.String(params.RegionName),
		Credentials: creds,
	}
	s3Client := s3.New(session.New(), config)
	creationTime := time.Since(start).Seconds() * 1000 // In milliseconds

	addParams := make(map[string]interface{})
	addParams["creationTime"] = creationTime

	// 将新的s3Client添加到缓存
	localCache.Set(key, s3Client, addParams)

	return s3Client
}

func batchRun(c *gin.Context) {
	reqs := make([]map[string]interface{}, 0)
	c.BindJSON(&reqs)
	logrus.Debug("req: ", reqs)

	// Aggreated results
	responses := make(map[string]interface{}, len(reqs))
	logrus.Debug("len of reqs", len(reqs))
	for i := range reqs {
		reqs[i]["concurrency"] = len(reqs)
	}
	wg := &sync.WaitGroup{}

	for _, req := range reqs {
		wg.Add(1)
		go parallel_exe(req, wg, responses)
	}

	// 当计数器为0时, 不再阻塞
	wg.Wait()
	logrus.Debug("responses: ", responses)
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

func initFunc(c *gin.Context) {
	c.JSON(http.StatusOK, "OK")
}

func setCacheConfig(c *gin.Context) {
	var config CacheConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	// 检查缓存大小
	if config.CacheStrategy != "Unbounded" && config.CacheSize <= 0 {
		logrus.Error("error: Cache size must be greater than 0")
		c.JSON(400, gin.H{"error": "Cache size must be greater than 0"})
		return
	}

	// 更新缓存
	localCache = NewLocalCache(config.CacheStrategy, config.CacheSize)

	c.JSON(200, gin.H{"message": "Cache configuration updated successfully"})
}

func cacheInfo(c *gin.Context) {
	c.JSON(http.StatusOK, localCache.cacheInfo())
}

func getFinalCacheInfo(c *gin.Context) {
	c.JSON(http.StatusOK, localCache.getFinalCacheInfo())
}

var localCache *LocalCache

func main() {
	logrus.SetLevel(logrus.InfoLevel)

	localCache = NewLocalCache("LRU", 10)
	route := gin.Default()
	route.POST("/run", run)
	route.POST("/batch_run", batchRun)
	route.GET("/status", stats)
	route.POST("/set_cache_config", setCacheConfig)
	route.POST("/init", initFunc)
	route.GET("/cache_info", cacheInfo)
	route.GET("/get_final_cache_info", getFinalCacheInfo)

	add := fmt.Sprintf(":%s", PROXY)
	route.Run(add)

}
