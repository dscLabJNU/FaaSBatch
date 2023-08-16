package main

import (
	"path/filepath"
	"time"

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

func getAWSBoto3Args(args AWSBoto3) map[string]interface{} {
	return map[string]interface{}{
		"aws_access_key_id":     args.AWSAccessKeyID,
		"aws_secret_access_key": args.AWSSecretAccessKey,
		"region_name":           args.RegionName,
	}
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

	// 这里你可以使用 s3Client 进行任何需要的操作

	elapsed := time.Since(start).Seconds() * 1000 // In milliseconds
	return bucketName, bucketKey, elapsed, s3Client
}

func function(args Args) map[string]interface{} {
	_, _, execTime, _ := getFunctionInstance(args)
	return map[string]interface{}{
		"exec_time":   execTime,
		"concurrency": args.Concurrency,
	}
}
