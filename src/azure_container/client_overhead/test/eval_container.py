from container import Container
import docker
import os
import time
from thread import ThreadWithReturnValue
import argparse
import multiprocessing
base_url = 'http://127.0.0.1:{}/{}'
client = docker.from_env()


def create_containers(image_name, num_containers, num_cores):
    container_pool = []
    print(f"Creating {num_containers} of containers")
    for i in range(1, num_containers+1):
        cpu_num = i % num_cores
        container_port = 8848 + i
        # create the container
        container = Container.create(
            client, image_name, container_port, 'exec', cpu_num)
        # init the container
        container.init()
        container_pool.append(container)
    return container_pool


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=[
                        "native", "optimize"], help="Select the type of load for concurrent testing")
    return parser.parse_args()


def invoke_requests(container_pool, concurrency, log_file):
    threads = []
    reqs = [
        {"duration": 0.01, "request_id": str(id), "concurrency": concurrency} for id in range(1, concurrency+1)
    ]
    for c in container_pool:
        t = ThreadWithReturnValue(
            target=c.send_batch_requests, args=(reqs,))
        threads.append(t)
        t.start()
    for t in threads:
        res = t.join()
    values = res.values()
    for value in values:
        
        print(f"{value['time_s3_create']},{value['mem_used']},{value['concurrency']}", file=log_file, flush=True)


if "__main__" == __name__:
    num_cores = multiprocessing.cpu_count()

    args = parse_args()
    image_name = f"boto3-client-{args.mode}"
    log_file = open(f"../logs/boto3_client_{args.mode}.csv", "w")
    print("time(ms),memory(MB),concurrency", file=log_file, flush=True)

    for i in range(1):
        # [1, 10]
        for concur in range(1, 11):
            # remove the labeled containers
            os.system(
                'docker rm -f $(docker ps -aq --filter label=boto3-client) >/dev/null 2>&1')

            # the number of cores is used to map the vcpu of each container
            container_pool = create_containers(
                image_name=image_name, num_containers=1, num_cores=num_cores)
            print(f"Concurrency: {concur}")
            invoke_requests(container_pool, concurrency=concur, log_file=log_file)
