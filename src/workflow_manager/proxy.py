from gevent import monkey
monkey.patch_all()
import os
import gevent
import json
from typing import Dict
import sys
sys.path.append('../../config')
import config
from workersp import WorkerSPManager
from mastersp import MasterSPManager
import docker
from flask import Flask, request
import requests
app = Flask(__name__)
docker_client = docker.from_env()
container_names = []


class Dispatcher:
    def __init__(self, data_mode: str, control_mode: str, info_addrs: Dict[str, str]) -> None:
        self.managers = {}
        if control_mode == 'WorkerSP':
            self.managers = {name: WorkerSPManager(
                sys.argv[1] + ':' + sys.argv[2], name, data_mode, addr) for name, addr in info_addrs.items()}
        elif control_mode == 'MasterSP':
            self.managers = {name: MasterSPManager(
                sys.argv[1] + ':' + sys.argv[2], name, data_mode, addr) for name, addr in info_addrs.items()}

    def get_state(self, workflow_name: str, request_id: str) -> WorkerSPManager:
        return self.managers[workflow_name].get_state(request_id)

    def trigger_function(self, workflow_name, state, function_name, no_parent_execution, azure_data):
        self.managers[workflow_name].trigger_function(
            state, function_name, no_parent_execution, azure_data)

    def clear_mem(self, workflow_name, request_id):
        self.managers[workflow_name].clear_mem(request_id)

    def clear_db(self, workflow_name, request_id):
        self.managers[workflow_name].clear_db(request_id)

    def del_state(self, workflow_name, request_id, master):
        self.managers[workflow_name].del_state(request_id, master)


dispatcher = Dispatcher(data_mode=config.DATA_MODE,
                        control_mode=config.CONTROL_MODE, info_addrs=config.FUNCTION_INFO_ADDRS)

# a new request from outside
# the previous function was done


@app.route('/request', methods=['POST'])
def req():
    """
    data = 
    {'request_id': '1682f0ab-d312-4dd9-8813-855400e6e351', 
    'workflow_name': 'azure_bench_app_00000007_cpu_native', '
    function_name': 'azure_func_00000016_cpu_native', 
    'no_parent_execution': True, 
    'azure_data': {
        'function_name': 'azure_func_00000016_cpu_native', 
        'duration': 1.055, 
        'input_n': 323}
        }
    """
    data = request.get_json(force=True, silent=True)
    request_id = data['request_id']
    workflow_name = data['workflow_name']
    function_name = data['function_name']
    azure_data = data.get("azure_data", None)
    no_parent_execution = data['no_parent_execution']
    # get the corresponding workflow state and trigger the function
    state = dispatcher.get_state(workflow_name, request_id)
    dispatcher.trigger_function(
        workflow_name, state, function_name, no_parent_execution, azure_data)
    return json.dumps({'status': 'ok'})


@app.route('/clear', methods=['POST'])
def clear():
    data = request.get_json(force=True, silent=True)
    workflow_name = data['workflow_name']
    request_id = data['request_id']
    master = False
    if 'master' in data:
        master = True
        # optional: clear results in center db
        dispatcher.clear_db(workflow_name, request_id)
    # must clear memory after each run
    dispatcher.clear_mem(workflow_name, request_id)
    # and remove state for every node
    dispatcher.del_state(workflow_name, request_id, master)
    return json.dumps({'status': 'ok'})


@app.route('/finalize_hit_rate', methods=['POST'])
def finalize_hit_rate():
    containers = docker_client.containers.list(filters={"label": "workflow"})
    log_file = open("./tmp/hit_rate_FaaSBatch.csv", "a")
    for c in containers:
        ip_add = c.attrs['NetworkSettings']['IPAddress']
        base_url = 'http://'+ip_add+':{}/{}'
        key_details = requests.get(base_url.format(5000, 'cache_info')).json()['key_cache_details']
        hits = sum([key_detail['hits'] for key_detail in key_details.values()])
        invos = sum([key_detail['invos'] for key_detail in key_details.values()])
        hit_rate = hits/invos
        total_cached_keys = requests.get(base_url.format(
            5000, 'total_cached_keys')).json()['total_cached_keys']
        
        print(f"{c.name},{hits},{invos},{hit_rate},{total_cached_keys}",
              file=log_file, flush=True)
    return json.dumps({'status': 'ok'})

{'key_hit_rates': {'0f3849cd6a0a352b94a716ecd705de9ab01cf739': 0.5, '0fda523c4f097ece6b5f7b347a91081b62cc4c85': 0.5, '2768491079a367b53353df614b485632e8ffc5c4': 0.5, '384ee2cf51e98e0c356d47870c8d3749ef6d9a91': 0.5, '64644439e4a7e784f9c791c1c536371a2faeeb3e': 0.5, '717be600321e04991998ada30720be99b629e8d4': 0.5, '781a973311ff558ae0d02970217d76a6efafacce': 0.5, '99fd40cdb3aa143885829f476d3e05ed9b6d5261': 0.5, '9edcc2dc8c498dd0534596cf44764c4ea630ac4a': 0.5, 'a7c2b5302dad8572923c15b063d43264c37ca5dd': 0.5}}
@app.route('/info', methods=['GET'])
def info():
    return json.dumps(container_names)


@app.route('/clear_container', methods=['GET'])
def clear_container():
    print('clearing containers')
    os.system('docker rm -f $(docker ps -aq --filter label=workflow)')
    return json.dumps({'status': 'ok'})


GET_NODE_INFO_INTERVAL = 0.1


def get_container_names():
    gevent.spawn_later(get_container_names)
    global container_names
    container_names = [container.attrs['Name']
                       for container in docker_client.containers.list()]


def print_strategy_info():
    if config.REQUEST_BATCHING:
        print(
            f"Running proxy with strategy = {config.STRATEGY}, dispatch_interval = {config.DISPATCH_INTERVAL}")
        if config.STRATEGY == "Kraken":
            print(f"SLO_quantail={config.SLO_quantail}")
    else:
        print(f"Running proxy with strategy = FaaSFlow")
from gevent.pywsgi import WSGIServer
import logging
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%H:%M:%S', level='INFO')
    server = WSGIServer((sys.argv[1], int(sys.argv[2])), app)
    print_strategy_info()
    server.serve_forever()
    gevent.spawn_later(GET_NODE_INFO_INTERVAL)
