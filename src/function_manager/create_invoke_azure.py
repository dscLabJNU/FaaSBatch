from container import Container
import docker
import os
import time
from thread import ThreadWithReturnValue
client = docker.from_env()
os.system(
    'docker rm -f $(docker ps -aq --filter label=workflow) >/dev/null 2>&1')
container_pool = []
num_containers = 3
print(f"Creating {num_containers} of containers")
for i in range(1, num_containers+1):
    print(f"Creating container {i}")
    container = Container.create(
        client, "azure_bench_func_00000016", 2222+i, 'exec')
    print("Init")
    container.init(workflow_name='azure_bench_app_00000007',
                   function_name='azure_bench_func_00000016')
    container_pool.append(container)
print("Invoke")

reqs = [{"duration": 1, "request_id": "111"},
        {"duration": 1, "request_id": "222"}, ]
start = time.time()
# res = container.send_batch_requests(reqs, [])
threads = []
for c in container_pool:
    t = ThreadWithReturnValue(
        target=c.send_batch_requests, args=(reqs, [],))
    threads.append(t)
    t.start()
batch_duration = time.time() - start

start = time.time()
for req in reqs:
    res = container.send_request(req)
normal_duration = time.time() - start
print(batch_duration, normal_duration)
