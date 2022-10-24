from locale import currency
import requests

base_url = 'http://127.0.0.1:{}/{}'

concurrency = 5
batch_reqs = [{"duration": 0.01, "function_id": str(id), "concurrency": concurrency, "input_n": 34} for id in range(1, concurrency+1)]
single_req = {"duration": 0.01, "function_id": "1", "concurrency": 1}

# r = requests.post(base_url.format(5000, 'run'), json=single_req)
r = requests.post(base_url.format(5000, 'batch_run'), json=batch_reqs)

print(r.json())

