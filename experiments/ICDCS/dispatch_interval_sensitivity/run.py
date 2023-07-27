from random import seed
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
from azure_function import AzureFunction
from azure_blob import AzureBlob
from utils import AzureTraceSlecter, AzureType, SamplingMode
import argparse
import os

repo = Repository()
TEST_PER_WORKFLOW = 2 * 60
TEST_CORUN = 2 * 60
TIMEOUT = 100
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
        # rep = requests.post(url, json=data)
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
    workflow_pool = []

    if mode == 'azure_bench':
        seed(5432)
        workflow_infos = yaml.load(open(
            f"{customize_azure.AZURE_BENCH_ADDR}/workflow_infos.yaml"), Loader=yaml.FullLoader)

        if AzureType.CPU in azure_type:
            # CPU function uses AzureFunction trace
            workflow_info = workflow_infos[AzureTraceSlecter.AzureFunction]
            azure = AzureFunction(workflow_info, azure_type)
            num_invos = 5000
        elif AzureType.IO in azure_type:
            num_invos = 10000
            # I/O function uses AzureBlob trace
            workflow_info = workflow_infos[AzureTraceSlecter.AzureBlob]
            azure = AzureBlob(workflow_info, azure_type)

        func_map_dict, app_map_dict = azure.load_mappers()

        eval_trace = azure.filter_df(
            app_map_dict=app_map_dict,
            num_invos=num_invos,
            mode=SamplingMode.Sequantial
        )

        print("Ploting RPS of the Azure dataset...")
        azure.plot_RPS(eval_trace.copy())

        if AzureType.IO in azure_type:
            # I/O function uses AzureBlob trace,
            # and uses AzureFunction trace to generate function invocation
            # TODO Optimize this redundancy logic (maybe sometime)
            azure_function_workflow_info = workflow_infos[AzureTraceSlecter.AzureFunction]
            azure_function = AzureFunction(
                azure_function_workflow_info, azure_type=azure_type)
            func_map_dict, app_map_dict = azure_function.load_mappers()
            azure_function_filtered = azure_function.filter_df(
                app_map_dict=app_map_dict,
                num_invos=num_invos,
                mode=SamplingMode.Sequantial
            )
            if len(azure_function_filtered['func']) < len(eval_trace):
                raise ValueError(
                    f"Not enough rows can be borrowed from AzureFunction trace, {len(eval_trace)} needed, only {len(azure_function_filtered['func'])} of rows ")

            # Borrow columns from AzureFunction trace
            eval_trace['func'] = azure_function_filtered['func']
            eval_trace['duration'] = azure_function_filtered['duration']
            eval_trace['app'] = azure_function_filtered['app']

        cnt = 0
        jobs = []
        trace_time = 0
        print("Running Azure dataset...")
        for _, row in eval_trace.iterrows():
            start_ts_sec, workflow_name, azure_data = prepare_invo_info(
                func_map_dict, app_map_dict, row, azure_type)
            trace_time = max(start_ts_sec, trace_time)
            jobs.append(gevent.spawn_later(start_ts_sec, analyze_azure_workflow,
                        workflow_name=workflow_name, azure_data=azure_data))
            workflow_pool.append(workflow_name)
            cnt += 1
            if cnt == num_invos:
                break

        print(cnt)
        print(f"This experiment will be done in {trace_time/60} mins")
        gevent.joinall(jobs)


def prepare_invo_info(func_map_dict, app_map_dict, row, azure_type):
    invo_ts = row['invo_ts']
    start_ts_sec = invo_ts.total_seconds()  # in seconds
    duration = row['duration']
    function_name = func_map_dict[row["func"]]
    workflow_name = app_map_dict[row['app']]
    input_n = int(row.get("input_n", 30))
    azure_data = {
        "function_name": function_name,
        "input_n": input_n,
    }
    if AzureType.CPU in azure_type:
        # CPU function uses AzureFunction trace
        addition_data = {
            "duration": duration,
        }

    elif AzureType.IO in azure_type:
        # I/O function uses AzureBlob trace
        addition_data = {
            "aws_boto3": {
                "aws_access_key_id": f"{row['AnonUserId']}_key_id",
                "aws_secret_access_key": f"{row['AnonUserId']}_access_key",
                "region_name": f"{row['AnonRegion']}",
                "bucket_name": f"{row['AnonBlobName']}{row['AnonBlobETag']}_name",
                "bucket_key": f"{row['AnonBlobName']}{row['AnonBlobETag']}_key",
                "read": row['Read']
            }
        }

    azure_data.update(addition_data)

    # print(f"Trigger {workflow_name}, {function_name} in {start_ts_sec} seconds")
    return start_ts_sec, workflow_name, azure_data


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=[
                        "azure_bench"], help="Select the benchmark suite")

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
