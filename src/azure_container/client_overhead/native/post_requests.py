import requests

base_url = 'http://127.0.0.1:{}/{}'

concurrency = 5
batch_reqs = [
    {
        "azure_data": {
            'function_name': f'azure_func_{id}',
            'duration': 0.109,
            'input_n': 34,
            'activate_SFS': True
        },
        "function_id": str(id),
        "concurrency": concurrency
    }
    for id in range(1, concurrency+1)]

single_req = {"duration": 0.01, "function_id": "1", "concurrency": 1,
              "azure_data": {
                  'function_name': f'azure_func_{id}',
                  'duration': 0.109,
                  'input_n': 34,
                  'active_SFS': True
              }, }

# r = requests.post(base_url.format(5000, 'run'), json=single_req)
r = requests.post(base_url.format(4000, 'batch_run'), json=batch_reqs)

print(r.json())

