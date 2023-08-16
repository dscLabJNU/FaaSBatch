package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)

const (
	Bucket = "openwhiskbucket"
	Folder = "finra/data"
)

type Args struct {
	AzureData   AzureData `json:"azure_data"`
	Concurrency int       `json:"concurrency"`
}

type AzureData struct {
	AWSBoto3 AWSBoto3 `json:"aws_boto3"`
}

type AWSBoto3 struct {
	ServiceName        string `json:"service_name"`
	AWSAccessKeyID     string `json:"aws_access_key_id"`
	AWSSecretAccessKey string `json:"aws_secret_access_key"`
	RegionName         string `json:"region_name"`
}

func getBucketKey() string {
	return filepath.Join(Folder, "portfolios.json")
}

func createS3Client(params AWSBoto3) *s3.S3 {

	creds := credentials.NewStaticCredentials(params.AWSAccessKeyID, params.AWSSecretAccessKey, "")
	config := &aws.Config{
		Region:      aws.String(params.RegionName),
		Credentials: creds,
	}

	s3Client := s3.New(session.New(), config)

	return s3Client
}

func getBucketName() string {
	return Bucket
}
func getFunctionInstance(args Args) (string, string, float64, *s3.S3) {
	start := time.Now()
	bucketName := getBucketName()
	bucketKey := getBucketKey()

	// 直接调用 createS3Client 函数并获取 S3 客户端
	s3Client := createS3Client(args.AzureData.AWSBoto3)

	elapsed := time.Since(start).Seconds() * 10000
	return bucketName, bucketKey, elapsed, s3Client
}

func function(args Args) map[string]interface{} {
	_, _, execTime, _ := getFunctionInstance(args)
	return map[string]interface{}{
		"exec_time":   execTime,
		"concurrency": args.Concurrency,
	}
}

func main() {
	if len(os.Args) != 6 {
		fmt.Println("Usage:", os.Args[0], "serviceName accessKeyID secretAccessKey regionName concurrency")
		return
	}

	serviceName := os.Args[1]
	accessKeyID := os.Args[2]
	secretAccessKey := os.Args[3]
	regionName := os.Args[4]
	concurrencyStr := os.Args[5]

	concurrency, err := strconv.Atoi(concurrencyStr)
	if err != nil {
		fmt.Println("Error converting concurrency to integer:", err)
		return
	}

	// 创建 Args 结构体
	args := Args{
		AzureData: AzureData{
			AWSBoto3: AWSBoto3{
				ServiceName:        serviceName,
				AWSAccessKeyID:     accessKeyID,
				AWSSecretAccessKey: secretAccessKey,
				RegionName:         regionName,
			},
		},
		Concurrency: concurrency, // 你可能需要将其转换为整数
	}

	// 调用 function 函数
	result := function(args)

	// 将结果序列化为 JSON 并输出到标准输出
	jsonResult, err := json.Marshal(result)
	if err != nil {
		fmt.Println("Error marshalling result:", err)
		return
	}
	fmt.Println(string(jsonResult))
}
