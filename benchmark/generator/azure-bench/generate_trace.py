import os
import yaml
import pandas as pd
import sys
import json
sys.path.append('../../../config')
import config

def parse_flat_workflow(functions, flat_workflow):
    for func_name in functions:
        function_info = {'name': func_name, "source": func_name,
                         "runtime": 1, "scale": 3, "mem_usage": 0.25}
        flat_workflow['functions'].append(function_info)
    return flat_workflow


def parse_function_info(workflow_name, functions, function_info):
    function_info['workflow'] = workflow_name
    for func_name in functions:
        function_info['functions'].append({
            "image": func_name,
            "name": func_name,
            'qos_requirement': 0.95,
            'qos_time': 100
        })
    return function_info


def write_yamls(flat_workflow, function_info, workflow_type, workflow_name):
    workflow_dir = f"./{workflow_type}/{workflow_name}"
    if not os.path.exists(workflow_dir):
        os.makedirs(workflow_dir)

    flat_workflow_yaml = open(
        f"{workflow_dir}/flat_workflow.yaml", 'w', encoding='utf-8')
    yaml.dump(flat_workflow, flat_workflow_yaml, sort_keys=False)

    function_info_yaml = open(
        f"{workflow_dir}/function_info.yaml", 'w', encoding='utf-8')
    yaml.dump(function_info, function_info_yaml, sort_keys=False)


def generate_workflows(df, workflow_names, workflow_type):

    with open(f"./{workflow_type}/func_mapper.json") as load_f:
        func_map_dict = json.load(load_f)

    with open(f"./{workflow_type}/app_mapper.json") as load_f:
        app_map_dict = json.load(load_f)

    for app, data in df.groupby('app'):
        workflow_name = app_map_dict[app]
        if workflow_name not in workflow_names:
            continue
        flat_workflow = {'functions': []}
        function_info = {'workflow': "", 'max_containers': 5, 'functions': []}
        print(f'generating workflow {workflow_name}')

        functions = list(
            map(lambda x: func_map_dict[x], data['func'].unique()))
        print(functions)
        flat_workflow = parse_flat_workflow(functions, flat_workflow)
        function_info = parse_function_info(
            workflow_name, functions, function_info)

        write_yamls(flat_workflow, function_info, workflow_type, workflow_name)


def process_and_dump(df, workflow_type, intensive, method):
    app_map = {app: f"azure_bench_app_{num+1:08}" for num,
               app in enumerate(df['app'].unique())}
    func_map = {func: f"azure_{intensive}_{method}_func_{num+1:08}" for num,
                func in enumerate(df['func'].unique())}
    with open(f"./{workflow_type}/func_mapper.json", 'w') as dump_f:
        dump_f.write(json.dumps(func_map))

    with open(f"./{workflow_type}/app_mapper.json", 'w') as dump_f:
        dump_f.write(json.dumps(app_map))


intensive_dict = {"io": ["optimize", "native"],
                  "cpu": ["native"]}
if __name__ == "__main__":
    data_dir = config.AZURE_DATA_DIR
    # Do not change the csv file, cause different df incurs different mapper json files
    df = pd.read_csv(
        f"{data_dir}/AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt")

    # Delete previous workflows
    os.system("rm -rf ./*workflows/")

    for intensive, methods in intensive_dict.items():
        for method in methods:
            workflow_type = f"{intensive}_workflows/{method}"
            os.system(f"mkdir -p {workflow_type}")

            process_and_dump(df, workflow_type=workflow_type,
                             intensive=intensive, method=method)
            workflow_infos = yaml.load(
                open("./workflow_infos.yaml"), Loader=yaml.FullLoader)
            for info in workflow_infos:
                """
                We generate all functions for each workflow, 
                meaning the number of functions may exceed that of the acutal invocked functions.
                Because we invoke functions in a specific time range, thus may not be covered all functions. 
                """
                generate_workflows(
                    df, info['workflow_names'], workflow_type=workflow_type)
