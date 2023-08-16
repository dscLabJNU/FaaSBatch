import requests
import os
base_url = 'http://127.0.0.1:{}/{}'
concurrency = 10
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
# requests.post(base_url.format(5000, 'set_cache_config'), json={"cache_strategy": "Unbounded"})
r = requests.post(base_url.format(5000, 'batch_run'), json=reqs)
total_exec = 0
for i, res in r.json().items():
    total_exec += res['exec_time']
print(r.json())
print(f"total execution time: {total_exec} ms")
