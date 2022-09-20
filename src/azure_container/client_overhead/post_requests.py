import requests
import argparse
from thread import ThreadWithReturnValue
base_url = 'http://127.0.0.1:{}/{}'

def post_batch_run(reqs):
    r = requests.post(base_url.format(5000, 'batch_run'), json=reqs)
    return r.json()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-concurrency", type=int, required=True, help="Concurrency of requests running in the same container")
    args = parser.parse_args()

  
    return args.concurrency


if __name__ == "__main__":

    concurrency = parse_args()

    threads = []
    reqs = [
        {"duration": 0.01, "request_id": str(id), "concurrency": concurrency} for id in range(1, concurrency+1)
    ]
    # init a container
    r = requests.post(base_url.format(5000, 'init'))

    t = ThreadWithReturnValue(target=post_batch_run, args=(reqs,))
    threads.append(t)
    t.start()
    for t in threads:
        res = t.join()
        print(res)
