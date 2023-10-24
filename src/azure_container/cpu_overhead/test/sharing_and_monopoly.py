from urllib import request
from container import Container
import docker
import subprocess
import os
import time
import threading
from multiprocessing import Process
base_url = 'http://127.0.0.1:{}/{}'
client = docker.from_env()


def create_container(image_name, port):

    container = Container.create(
        client, image_name, port, 'exec')
    global containers
    containers.append(container)


def fake_create(num_containers):
    return [f"container_{i}" for i in range(num_containers)]


def parallel_create_containers(num_containers, image_name, port_base):
    # containers = fake_create(num_containers=num_containers)
    print("Clearing previous containers.")
    os.system(
        'docker rm -f $(docker ps -aq --filter label=azure-cpu) >/dev/null 2>&1')
    time.sleep(5)
    global containers
    containers = []

    threads = []
    for i in range(num_containers):
        t = threading.Thread(target=create_container,
                             args=(image_name, port_base+i, ))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    return containers


def invoke_container(container, reqs, log_file):
    res = container.send_batch_requests(data=reqs)
    print(res.values())
    for res_sub in list(res.values()):
        # print(res_sub)
        queue_time = res_sub.get("queue_time", 0)
        print(
            f"{container.container.name},{res_sub['exec_time']},{queue_time}", file=log_file, flush=True)
    return res


def invoke_block(container, num_requests, log_file):
    print(
        f"Invoke {num_requests} of requests to {container.container.id} instance...")
    reqs = [
        {
            "azure_data": {
                'function_name': f'azure_func_{id}',
                'input_n': 34,
                'activate_SFS': False  # Only for evaluating cpu-native
            },
            "function_id": str(id),
            "concurrency": num_requests
        } for id in range(1, num_requests+1)
    ]
    invoke_container(container, reqs, log_file)


def mapping_requests(num_requests, container_pool, log_file):
    num_containers = len(container_pool)
    avg_batch_size = num_requests // num_containers
    remainder = num_requests % num_containers

    events = []
    total = 0
    i = 1
    for server_container in container_pool:
        real_batch_size = avg_batch_size
        if i <= remainder:
            # 将前面remainder个容器的batch大小加一，避免无法整除的情况
            real_batch_size += 1
            i += 1
        p = Process(target=invoke_block, args=(
            server_container, real_batch_size, log_file,))
        total += real_batch_size
        events.append(p)
    print(f"Total request: {total}")
    start = time.time()
    for p in events:
        p.start()
    for p in events:
        p.join()


if "__main__" == __name__:
    """
    This script compares the performance between the following two modes across different concurrency:
    (1) sharing: All requests are executed inside a single container in parallel
    (2) monopoly: Each requests is executed in one single container separately
    """
    port_base = 8848
    modes = ['sharing', "monopoly"]
    concurrency_list = [10, 20, 40, 80, 160, 320, 640]
    for N in concurrency_list:
        for mode in modes:
            mem_log_file = open(f"../logs/{mode}_{N}_reqs_mem.csv", "w")
            log_file = open(f"../logs/{mode}_{N}_reqs.csv", 'w')
            print("container_name,exec_time(ms),queue_time(ms)",
                  file=log_file, flush=True)
            if mode == 'sharing':
                image_name = f"azure-cpu-optimize"
                # Only create a single container
                container_pool = parallel_create_containers(
                    num_containers=1, image_name=image_name, port_base=port_base)

            elif mode == 'monopoly':
                image_name = f"azure-cpu-native"
                # Create N of contianes in parallel
                container_pool = parallel_create_containers(
                    image_name=image_name, num_containers=N, port_base=port_base)

            subprocess.Popen(['bash', '-c', 
                'cd /home/vagrant/openwhisk-resource-monitor/; bash monitor_resources.sh'], 
                stdout=mem_log_file)
            print(f"{len(container_pool)} of containers have been created")

            # Maps N requests to the containers
            mapping_requests(
                num_requests=N, container_pool=container_pool, log_file=log_file)
            subprocess.run("ps -ef | grep -v grep |grep -E 'monitor_resources' | awk '{print $2}'| xargs kill -9", shell=True)
