import requests
import os
base_url = 'http://127.0.0.1:{}/{}'
concurrency = 3
BUCKET = "openwhiskbucket"
FOLDER = "finra/data"
PORTFOLIOS = "portfolios.json"

reqs = [
    {"duration": 0.01,
     "function_id": str(id),
     "concurrency": concurrency,
     "aws_boto3": {
         "aws_access_key_id": "AKIAUDE724LEOTYERSHO",
         "aws_secret_access_key": "4c5Lw1uXQM0ZFHm",
         "region_name": f"ap-southeast-{id}",
         "bucket_name": "bucket_name",
         "bucket_key": os.path.join(FOLDER, PORTFOLIOS)
     },
     } for id in range(1, concurrency+1)
]
r = requests.post(base_url.format(5000, 'batch_run'), json=reqs)
print(r.json())
