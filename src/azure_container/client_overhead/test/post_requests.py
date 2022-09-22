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
    parser.add_argument("-file", type=str, required=True, help="Log file name")
    args = parser.parse_args()

  
    return args.concurrency, args.file


if __name__ == "__main__":

    concurrency, log_file_name = parse_args()
    log_file = open(log_file_name, 'a')

    threads = []
    reqs = [
        {"duration": 0.01, "function_id": str(id), "concurrency": concurrency} for id in range(1, concurrency+1)
    ]
    # init a container
    # r = requests.post(base_url.format(5000, 'init'))

    t = ThreadWithReturnValue(target=post_batch_run, args=(reqs,))
    threads.append(t)
    t.start()
    for t in threads:
        res = t.join()
    values = res.values()
    for value in values:
        print(f"{value['time_s3_create']},{value['mem_used']},{value['concurrency']}", file=log_file, flush=True)
