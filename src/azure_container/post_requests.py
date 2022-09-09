import requests
from thread import ThreadWithReturnValue
base_url = 'http://127.0.0.1:{}/{}'

r = requests.post(base_url.format(5000, 'init'))

reqs = [
    {"duration": 1, "request_id": "111"},
    {"duration": 1, "request_id": "222"},
]


def post_batch_run(reqs):
    r = requests.post(base_url.format(5000, 'batch_run'), json=reqs)
    return r.json()


threads = []
for i in range(3):
    reqs = [
        {"duration": 1, "request_id": str(i)},
        {"duration": 1, "request_id": str(i+1)},
    ]
    t = ThreadWithReturnValue(target=post_batch_run, args=(reqs,))
    threads.append(t)
    t.start()
for t in threads:
    res = t.join()
    print(res)
