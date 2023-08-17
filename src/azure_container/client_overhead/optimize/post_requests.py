import requests
import os
base_url = 'http://127.0.0.1:{}/{}'
concurrency = 20
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
experiment_settings = [
    {"cache_strategy": "LRU", "cache_size": 10},
    {"cache_strategy": "Unbounded"},
    {"cache_strategy": "GDSF", "cache_size": 10}
]

experiment_results_cold = {}
experiment_results_warm = {}
strategies = []
for setting in experiment_settings:
    cache_strategy = setting['cache_strategy']
    strategies.append(cache_strategy)
    cache_config = {
        "cache_strategy": cache_strategy
    }
    if "cache_size" in setting:
        cache_config["cache_size"] = setting["cache_size"]

    # 进行 cold 执行
    total_exec = 0
    requests.post(base_url.format(5000, 'set_cache_config'), json=cache_config)  # 只在 cold 执行时设置
    rjson = requests.post(base_url.format(5000, 'batch_run'), json=reqs).json()
    for index, r in rjson.items():
        total_exec += r['exec_time']
    experiment_results_cold[cache_strategy] = f"{total_exec} ms"

    # 进行 warm 执行
    total_exec = 0
    rjson = requests.post(base_url.format(5000, 'batch_run'), json=reqs).json()
    
    
    # EVALUATION METRICS   
    cache_info = requests.get(base_url.format(5000, 'cache_info')).json()
    total_cached_keys = requests.get(base_url.format(5000, 'total_cached_keys')).json()
    print(total_cached_keys)
    for index, r in rjson.items():
        total_exec += r['exec_time']
    experiment_results_warm[cache_strategy] = f"{total_exec} ms"

# 打印结果
for strategy in strategies:
    print(f"Strategy: {strategy} tooks {experiment_results_cold[strategy]} for cold execution")
    print(f"Strategy: {strategy} tooks {experiment_results_warm[strategy]} for warm execution")
