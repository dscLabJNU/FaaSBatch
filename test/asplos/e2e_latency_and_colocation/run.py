from gevent import monkey
monkey.patch_all()
import uuid
import requests
import sys
sys.path.append('..')
sys.path.append('../../../config')
from repository import Repository
import config
import pandas as pd
import time
import gevent
import yaml
import customize_azure
from azure import Azure
import argparse
import os

repo = Repository()
TEST_PER_WORKFLOW = 2 * 60
TEST_CORUN = 2 * 60
TIMEOUT = 60
e2e_dict = {}


def run_workflow(workflow_name, request_id, azure_data=None):
    url = 'http://' + config.GATEWAY_ADDR + '/run'
    data = {'workflow': workflow_name, 'request_id': request_id}
    if azure_data:
        data.update({
            "azure_data": azure_data
        })
    try:
        rep = requests.post(url, json=data, timeout=TIMEOUT)
        return rep.json()['latency']
    except Exception:
        print(f'{workflow_name} timeout')
        return 1000


def analyze_azure_workflow(workflow_name, azure_data):
    global e2e_dict
    id = str(uuid.uuid4())
    e2e_latency = run_workflow(workflow_name, id, azure_data)
    e2e_dict[workflow_name] = e2e_latency


def analyze_workflow(workflow_name, mode):
    global e2e_dict
    total = 0
    start = time.time()
    e2e_total = 0
    timeout = 0
    LIMIT = TEST_PER_WORKFLOW if mode == 'single' else TEST_CORUN
    while timeout < 5 and (total < 3 or time.time() - start <= LIMIT):
        total += 1
        id = str(uuid.uuid4())
        print(f'----firing workflow {workflow_name}----', id)
        e2e_latency = run_workflow(workflow_name, id)
        if total > 2:
            if e2e_latency > 100:
                total = total - 1
                timeout = timeout + 1
            else:
                e2e_total += e2e_latency
                print('e2e_latency: ', e2e_latency)
    if timeout >= 5:
        print(f'{workflow_name} e2e_latency: timeout')
        e2e_dict[workflow_name] = 'timeout'
    else:
        e2e_latency = e2e_total / (total - 2)
        print(f'{workflow_name} e2e_latency: ', e2e_latency)
        e2e_dict[workflow_name] = e2e_latency


def analyze(mode, results_dir, azure_type=None):
    global e2e_dict
    workflow_pool = ['cycles', 'epigenomics', 'genome', 'soykb',
                     'video', 'illgal_recognizer', 'fileprocessing', 'wordcount']
    # workflow_pool = ['cycles', 'epigenomics', 'genome', 'soykb']
    # workflow_pool = ['genome', 'genome', 'genome', 'genome', 'genome']

    if mode == 'azure_bench':
        workflow_pool.clear()
        workflow_infos = yaml.load(open(
            f"{customize_azure.AZURE_BENCH_ADDR}/workflow_infos.yaml"), Loader=yaml.FullLoader)
        workflow_info = workflow_infos[0]
        azure = Azure(workflow_info, azure_type)

        df = azure.df
        func_map_dict, app_map_dict = azure.load_mappers()
        filter_df = azure.filter_df(app_map_dict)

        cnt = 0
        jobs = []
        print("Running Azure dataset...")
        for i, row in filter_df.iterrows():
            start_ts_sec, workflow_name, azure_data = prepare_invo_info(
                func_map_dict, app_map_dict, row)
            # if "azure_func_00000410" not in azure_data['function_name']:
            # continue
            jobs.append(gevent.spawn_later(start_ts_sec, analyze_azure_workflow,
                        workflow_name=workflow_name, azure_data=azure_data))
            # jobs.append(gevent.spawn(analyze_azure_workflow, workflow_name=workflow_name, azure_data=azure_data))
            workflow_pool.append(workflow_name)
            cnt += 1
            if cnt == 200:
                break

        print(cnt)
        gevent.joinall(jobs)
    if mode == 'single':
        for workflow in workflow_pool:
            analyze_workflow(workflow, mode)
    elif mode == 'corun':
        jobs = []
        for i, workflow_name in enumerate(workflow_pool):
            jobs.append(gevent.spawn_later(
                i * 5, analyze_workflow, workflow_name, mode))
        gevent.joinall(jobs)
    print(e2e_dict)
    e2e_latencies = []
    for workflow in workflow_pool:
        e2e_latencies.append(e2e_dict[workflow])
    df = pd.DataFrame({'workflow': workflow_pool,
                      'e2e_latency': e2e_latencies})
    csv_name = f"{results_dir}/{mode}_{azure_type if mode == 'azure_bench' else 'normal'}.csv"
    df.to_csv(csv_name, index=False)


def prepare_invo_info(func_map_dict, app_map_dict, row):
    invo_ts = row['invo_ts']
    start_ts_sec = invo_ts.total_seconds()  # in seconds
    duration = row['duration']
    function_name = func_map_dict[row["func"]]
    workflow_name = app_map_dict[row['app']]
    # duration = 2.22551
    azure_data = {
        "function_name": function_name,
        "duration": duration,
        "input_n": 30
    }
    # print(f"duration of {function_name} is {duration}")
    print(
        f"Trigger {workflow_name}, {function_name} in {start_ts_sec} seconds")
    return start_ts_sec, workflow_name, azure_data


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=[
                        "single", "corun", "azure_bench"], help="Select the benchmark suite")

    parser.add_argument("--azure_type", type=str, required='azure_bench' in sys.argv, choices=[
                        "cpu_native", "cpu_optimize", "io_native", "io_optimize"], help="Select the intensive type in which azure_bench mode")
    return parser.parse_args()


if __name__ == '__main__':
    results_dir = './results'
    os.system(f"mkdir -p {results_dir}")
    args = parse_args()
    repo.clear_couchdb_results()
    repo.clear_couchdb_workflow_latency()
    analyze(args.mode, results_dir, args.azure_type)
