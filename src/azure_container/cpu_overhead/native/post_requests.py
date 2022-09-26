from locale import currency
import requests

base_url = 'http://127.0.0.1:{}/{}'

concurrency = 2
reqs = [
        {"duration": 0.01, "function_id": str(id), "concurrency": concurrency} for id in range(1, concurrency+1)
    ]

r = requests.post(base_url.format(5000, 'batch_run'), json=reqs)
print(r.json())

