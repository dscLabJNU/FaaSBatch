from container import Container
import docker
import os
import time
from thread import ThreadWithReturnValue
import argparse
import multiprocessing
base_url = 'http://127.0.0.1:{}/{}'
client = docker.from_env()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=[
                        "native", "optimize"], help="Select the type of load for concurrent testing")
    return parser.parse_args()


if "__main__" == __name__:
    num_cores = multiprocessing.cpu_count()

    args = parse_args()
    proxy_dir = f'../{args.mode}'
    log_file_name = f"../logs/boto3_host_{args.mode}.csv"
    log_file = open(log_file_name, "w")
    print("time(ms),memory(MB),concurrency", file=log_file, flush=True)
    os.system(
        "sudo kill $(ps -ef | grep proxy.py | grep -v grep | awk '{print $2}')")

    for i in range(5):
        for concur in range(1, 11):
            os.system(f"nohup python {proxy_dir}/proxy.py &")
            time.sleep(0.5)
            print(f"Concurrency: {concur}")

            os.system(f"python post_requests.py -c {concur} -file {log_file_name}")

            os.system(
                "sudo kill $(ps -ef | grep proxy.py | grep -v grep | awk '{print $2}')")
