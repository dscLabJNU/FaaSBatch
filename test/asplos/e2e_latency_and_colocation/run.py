from gevent import monkey
monkey.patch_all()
import uuid
import requests
import getopt
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

repo = Repository()
TEST_PER_WORKFLOW = 2 * 60
TEST_CORUN = 2 * 60
TIMEOUT = 60
e2e_dict = {}

def run_workflow(workflow_name, request_id, azure_data=None):
    url = 'http://' + config.GATEWAY_ADDR + '/run'
    data = {'workflow':workflow_name, 'request_id': request_id}
    if azure_data:
        data.update({
                "azure_bench": True,
                "duration":azure_data['duration'], 
                "function_name": azure_data['function_name']
                })
    try:
        rep = requests.post(url, json=data, timeout=TIMEOUT)
        return rep.json()['latency']
    except Exception:
        print(f'{workflow_name} timeout')
        return 1000

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

def analyze(mode, datamode):
    global e2e_dict
    workflow_pool = ['cycles', 'epigenomics', 'genome', 'soykb', 'video', 'illgal_recognizer', 'fileprocessing', 'wordcount']
    # workflow_pool = ['cycles', 'epigenomics', 'genome', 'soykb']
    workflow_pool = ['genome', 'genome', 'genome', 'genome', 'genome']
    
    if mode == 'azure_bench':
        workflow_infos = yaml.load(open(f"{customize_azure.AZURE_BENCH_ADDR}/workflow_infos.yaml"), Loader=yaml.FullLoader)
        workflow_info = workflow_infos[0]
        azure = Azure(workflow_info)

        df = azure.df
        func_map_dict, app_map_dict = azure.load_mappers()
        filter_df = azure.filter_df(app_map_dict)
        
        cnt = 0
        jobs = []
        print("Running Azure dataset...")
        for i, row in filter_df.iterrows():
            start_ts_sec, workflow_name, azure_data = prepare_invo_info(func_map_dict, app_map_dict, row)
            jobs.append(gevent.spawn_later(start_ts_sec, run_workflow, workflow_name=workflow_name, request_id=str(uuid.uuid4()), azure_data=azure_data))
            print(workflow_name)
            cnt += 1
            # if cnt == 10:
                # break

        print(cnt)
        gevent.joinall(jobs)
        return
    if mode == 'single':
        for workflow in workflow_pool:
            analyze_workflow(workflow, mode)
    elif mode == 'corun':
        jobs = []
        for i, workflow_name in enumerate(workflow_pool):
            jobs.append(gevent.spawn_later(i * 5, analyze_workflow, workflow_name, mode))
        gevent.joinall(jobs)
    print(e2e_dict)
    e2e_latencies = []
    for workflow in workflow_pool:
        e2e_latencies.append(e2e_dict[workflow])
    df = pd.DataFrame({'workflow': workflow_pool, 'e2e_latency': e2e_latencies})
    df.to_csv(f'{datamode}_{mode}.csv')

def prepare_invo_info(func_map_dict, app_map_dict, row):
    invo_ts = row['invo_ts']
    start_ts_sec = invo_ts.total_seconds() # in seconds
    duration = row['duration']
    function_name = func_map_dict[row["func"]]
    workflow_name = app_map_dict[row['app']]
    duration = 2.22551
    azure_data = {
                "function_name": function_name,
                "duration": duration
            }
    # print(f"duration of {function_name} is {duration}")
    print(f"Trigger {workflow_name}, {function_name} in {start_ts_sec}")
    return start_ts_sec,workflow_name,azure_data

if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:],'',['mode=', 'datamode='])
    repo.clear_couchdb_results()
    repo.clear_couchdb_workflow_latency()
    for name, value in opts:
        if name == '--mode':
            mode = value
        elif name == '--datamode':
            datamode = value
    analyze(mode, datamode)
