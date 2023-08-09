import requests
import os
import const
base_url = 'http://127.0.0.1:{}/{}'
concurrency = 3
BUCKET = "openwhiskbucket"
FOLDER = "finra/data"
PORTFOLIOS = "portfolios.json"

reqs = [
    {"duration": 0.01,
     "function_id": str(id),
     "concurrency": concurrency,
     "azure_data": {
         "aws_boto3": {
             "aws_access_key_id": "AKIAUDE724LEOTYERSHO",
             "aws_secret_access_key": "4c5Lw1uXQM0ZFHm",
             "region_name": f"ap-southeast-{id}",
             "bucket_name": "bucket_name",
             "bucket_key": os.path.join(FOLDER, PORTFOLIOS),
             "read": True
         }
     },
     } for id in range(1, concurrency+1)
]
r = requests.post(base_url.format(const.PROXY_PORT, "set_strategy"),
                  json={"cache_strategy": "IdelCache", "cache_size": None})
r = requests.post(base_url.format(const.PROXY_PORT, 'batch_run'), json=reqs)
r = requests.get(base_url.format(const.PROXY_PORT, 'cache_info'))
print(r.json())
