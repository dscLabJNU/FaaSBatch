from random import seed
from gevent import monkey
monkey.patch_all()
import uuid
import requests
import sys
sys.path.append('..')
sys.path.append('../../../config')

import config
import pandas as pd
import time
import gevent
import yaml
import customize_azure
from azure_function import AzureFunction
from azure_blob import AzureBlob
from utils import AzureTraceSlecter, AzureType, SamplingMode
import utils
import argparse
import os
from requests.exceptions import Timeout, RequestException
from collections import Counter

TEST_PER_WORKFLOW = 2 * 60
TEST_CORUN = 2 * 60
TIMEOUT = 100
e2e_dict = {}
completed_jobs = 0
AWS_HASH_KEY_COUNTER = []


def run_workflow(workflow_name, request_id, azure_data=None):
    url = 'http://' + config.GATEWAY_ADDR + '/run'
    data = {'workflow': workflow_name, 'request_id': request_id}
    if azure_data:
        data.update({
            "azure_data": azure_data
        })
    try:
        rep = requests.post(url, json=data, timeout=TIMEOUT)
        latency = rep.json()['latency']
        return latency
    except Timeout:
        print(f'{workflow_name} timeout')
    except KeyError:
        print(f'{workflow_name} JSON does not contain latency')
    except ValueError:
        print(rep.text)
        print(f'{workflow_name} response could not be decoded as JSON')
    except RequestException as e:
        print(f'{workflow_name} request failed with exception: {e}')
    except Exception as e:
        print(f'{workflow_name} unexpected exception: {e}')

    return 1000


def analyze_azure_workflow(workflow_name, azure_data, num_invos):
    global completed_jobs
    id = str(uuid.uuid4())
    e2e_latency = run_workflow(workflow_name, id, azure_data)
    completed_jobs += 1
    print(f"\r{completed_jobs}/{num_invos} of jobs are completed", end='', flush=True)


def analyze(mode, cache_data, azure_type=None):
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
            num_invos = 2000
        elif AzureType.IO in azure_type:
            num_invos = 2000
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
            azure_function.plot_RPS(azure_function_filtered.copy())
            if len(azure_function_filtered['func']) < len(eval_trace):
                raise ValueError(
                    f"Not enough rows can be borrowed from AzureFunction trace, {len(eval_trace)} needed, only {len(azure_function_filtered['func'])} of rows ")

            # Borrow columns from AzureFunction trace
            eval_trace['func'] = azure_function_filtered['func']
            eval_trace['duration'] = azure_function_filtered['duration']
            eval_trace['app'] = azure_function_filtered['app']
            eval_trace['invo_ts'] = azure_function_filtered['invo_ts']

        cnt = 0
        jobs = []
        trace_time = 0
        print("Running Azure dataset...")
        for _, row in eval_trace.iterrows():
            start_ts_sec, workflow_name, azure_data = prepare_invo_info(
                func_map_dict, app_map_dict, row, azure_type, cache_data)
            trace_time = max(start_ts_sec, trace_time)
            jobs.append(gevent.spawn_later(start_ts_sec, analyze_azure_workflow,
                        workflow_name=workflow_name, azure_data=azure_data, num_invos=num_invos))
            workflow_pool.append(workflow_name)
            cnt += 1
            if cnt == num_invos:
                break

        print(f"This experiment ({cnt} of invocations) will be done in {trace_time/60} mins")
        gevent.joinall(jobs)
        plot_PDF(Counter(AWS_HASH_KEY_COUNTER))
               
        """
        Container lifetime is set on function_group.py
        The hit rate is automatically recorded for containers that reach the lifetime, 
        but for containers that end the experiment but do not reach the lifetime, 
        we actively record the hit ratio so that we can start the next experiment early.
        """
        requests.post(f'http://{config.MASTER_HOST}/finalize_hit_rate')

def plot_PDF(data: dict):
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.grid": True, 'grid.linestyle': '-.'})
    fig, ax = plt.subplots(figsize=(5, 1.5))
    sns.ecdfplot(data=data.values(), ax=ax, legend=False)

    ax.set_xscale('log', base=10)
    xticks_values = [1, 10, 10**2, 10**3, 10**4]
    ax.set_xticks(xticks_values)
    plt.xlabel("Amount of reqeusts", weight='bold', fontsize=12)
    plt.ylabel("CDF", weight='bold', fontsize=12)
    fig.savefig("imgs/AzureBlobRequestsPDF.pdf", bbox_inches='tight')


def prepare_invo_info(func_map_dict, app_map_dict, row, azure_type, cache_data):
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
                "cache_strategy": cache_data['cache_strategy'],
                "cache_size": cache_data['cache_size'],
                "aws_access_key_id": f"{row['AnonUserId']}_key_id",
                "aws_secret_access_key": f"{row['AnonUserId']}_access_key",
                "region_name": f"{row['AnonRegion']}",
            }
        }
        AWS_HASH_KEY_COUNTER.append(utils.hash_string(str(addition_data.get("aws_boto3"))))

    azure_data.update(addition_data)

    # print(f"Trigger {workflow_name}, {function_name} in {start_ts_sec} seconds")
    return start_ts_sec, workflow_name, azure_data


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, required=True, choices=[
                        "azure_bench"], help="Select the benchmark suite")

    parser.add_argument("--azure_type", type=str, required='azure_bench' in sys.argv, choices=[
                        "cpu_native", "cpu_optimize", "io_native", "io_optimize"], 
                        help="Select the intensive type in which azure_bench mode")
    
    parser.add_argument("--cache_strategy", type=str, required=True, choices=[
                        "LRU", "LFU", "GDSF", "IdelCache", "Random", "InfiniteCache"], help="Select the cache strategy")
    parser.add_argument("--cache_size", type=int, required=False, help="Indicate the cache size")
    return parser.parse_args()


if __name__ == '__main__':
    results_dir = './results'
    os.system(f"mkdir -p {results_dir}")
    args = parse_args()
    
    # Scheduling the cache items inside containers
    cache_data = {
        "cache_strategy": args.cache_strategy,
        "cache_size": args.cache_size
    }
    print(cache_data)
    analyze(args.mode, cache_data, args.azure_type)
