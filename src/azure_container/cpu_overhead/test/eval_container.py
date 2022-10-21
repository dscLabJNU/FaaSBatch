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
        container_port = 8848 + i
        bind_cpus = [i for i in range(num_cores)]
        # create the container
        print(f"bind core {bind_cpus} to this container")
        container = Container.create(
            client, image_name, container_port, 'exec', bind_cpus)
        # init the container
        # container.init()
        container_pool.append(container)
    return container_pool


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=[
                        "native", "optimize"], help="Select the type of load for concurrent testing")
    return parser.parse_args()


def invoke_requests(container_pool, concurrency, log_file=None):
    threads = []
    reqs = [
        {"duration": 0.01, "function_id": str(id), "concurrency": concurrency,"inpur_n": 31} for id in range(1, concurrency+1)
    ]
    for c in container_pool:
        t = ThreadWithReturnValue(
            target=c.send_batch_requests, args=(reqs,))
        threads.append(t)
        t.start()
    start = time.time()
    for t in threads:
        res = t.join()
    invocatino_latency = time.time() - start
    if log_file:
        print(f"{invocatino_latency*1000},{concurrency}", file=log_file, flush=True)

if "__main__" == __name__:
    num_cores = multiprocessing.cpu_count()

    args = parse_args()
    image_name = f"azure-cpu-{args.mode}"
    os.system("mkdir -p ../logs")
    log_file = open(f"../logs/azure_cpu_{args.mode}.csv", "w")
    print("invo_latency(ms),concurrency", file=log_file, flush=True)
    for i in range(1):
        # [1, 10]
        for concur in range(1,11):
            # remove the labeled containers
            os.system(
                'docker rm -f $(docker ps -aq --filter label=azure-cpu) >/dev/null 2>&1')

            # the number of cores is used to map the vcpu of each container
            # The performance gets worse if we dont map a specific vcpu
            # we turn it off or on in container.py#Container@create
            container_pool = create_containers(
                image_name=image_name, num_containers=1, num_cores=concur)
            invoke_requests(container_pool, concurrency=concur, log_file=log_file)
            print(f"Currency: {concur}")
