import time
import os
import psutil
import boto3

BUCKET = "openwhiskbucket"
FOLDER = "finra/data"

PORTFOLIOS = "portfolios.json"


def get_s3_instance(args):
    service_name = args.get("service_name", 's3')
    aws_access_key_id = args.get("aws_access_key_id", "AKIAUDE724LEOTYERSHO")
    aws_secret_access_key = args.get(
        "aws_secret_access_key", "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")
    region_name = args.get("region_name", "ap-southeast-1")
    bucket_name = args.get("bucket_name", BUCKET)
    bucket_key = args.get("bucket_key", os.path.join(FOLDER, PORTFOLIOS))
    # close ssl certification for convinence
    start = time.time()
    session = boto3.session.Session()
    s3 = session.client(service_name=service_name,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        region_name=region_name,
                        use_ssl=False)
    time_s3_create = time.time() - start
    return s3, bucket_name, bucket_key, time_s3_create * 1000


def main(args=None):
    if not args:
        concurrency = globals()['concurrency']
    else:
        concurrency = args['concurrency']
    # log_file = open(f"./logs/s3_resource.csv", 'a')

    mem_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    s3, bucket_name, bucket_key, exec_time = get_s3_instance(args=args['azure_data'].get("aws_boto3", {}))
    # portfolios = s3.get_object(Bucket=bucket_name, Key=bucket_key)[
    #         'Body'].read().decode("utf-8")
    # print(portfolios)
    mem_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    mem_used = mem_after - mem_before
    # print(f"{time_s3_create},{mem},{concurrency}", file=log_file, flush=True)
    # mem_info = {
    #     "mem_before": mem_before,
    #     "mem_after": mem_after,
    #     "mem_used": mem_used,
    # }
    return {"exec_time": exec_time, "mem_used": mem_used, "concurrency": concurrency}


if __name__ == "__main__":
    print(main({"concurrency": 2, "azure_data":{}}))
