import os
import yaml
import pandas as pd 
import sys
import json
sys.path.append('../../../config')
import config

def parse_flat_workflow(format_func_name, flat_workflow):
    function_info = {'name': format_func_name, "source":format_func_name,"runtime":1,"scale":3,"mem_usage":0.25}
    flat_workflow['functions'].append(function_info)
    return flat_workflow

def parse_function_info(format_func_name, function_info, workflow_name=None):
    function_info['workflow'] = workflow_name or format_func_name
    function_info['functions'].append({
        "image": "azure-bench",
        "name": format_func_name,
        'qos_requirement': 0.95,
        'qos_time': 100
    })
    return function_info

def write_yamls(flat_workflow, function_info, format_func_name):
    workflow_dir = f"./workflows/{format_func_name}"
    if not os.path.exists(workflow_dir):
        os.makedirs(workflow_dir)

        
    flat_workflow_yaml = open(f"{workflow_dir}/flat_workflow.yaml", 'w', encoding='utf-8')
    yaml.dump(flat_workflow, flat_workflow_yaml, sort_keys=False)

    function_info_yaml = open(f"{workflow_dir}/function_info.yaml", 'w', encoding='utf-8')
    yaml.dump(function_info, function_info_yaml, sort_keys=False)
    

def generate_workflows(parse_flat_workflow, parse_function_info, write_yamls, df):
    # 将func转化可读的为function_name，编号从00000001开始
    func_map = {func: f"azure_bench_{num+1:08}" for num, func in enumerate(df['func'].unique())}
    map_json = json.dumps(func_map)
    json_file = open("./func_mapper.json", 'w')
    json_file.write(map_json)

    with open("./func_mapper.json") as load_f:
        func_map_dict = json.load(load_f)

    for func in df['func'].unique():
    # Parse each specific workflow
        flat_workflow = {'functions': []}
        function_info = {'workflow': "", 'max_containers': 5, 'functions': []}
        format_func_name = func_map_dict[func]
        print('\r' + f'generating workflow {format_func_name}...', end='', flush=True)

        flat_workflow = parse_flat_workflow(format_func_name, flat_workflow)
        function_info = parse_function_info(format_func_name, function_info)
        write_yamls(flat_workflow, function_info, format_func_name)

    print()
    return func_map_dict

def genreate_all_bench():

    all_flat_workflow = {'functions': []}
    all_function_info = {'workflow': "", 'max_containers': 5, 'functions': []}

    for func in df['func'].unique():
        # Parse all workflows, only for registry the function to the couch db
        format_func_name = func_map_dict[func]
        print('\r' + f'generating workflow azrure_bench_all ...', end='', flush=True)

        all_flat_workflow = parse_flat_workflow(format_func_name, all_flat_workflow)
        all_function_info = parse_function_info(format_func_name, all_function_info, "azure_bench_all")
    write_yamls(all_flat_workflow, all_function_info, 'azure_bench_all')
    print()

if __name__ == "__main__":
    data_dir = config.AZURE_DATA_DIR
    df = pd.read_csv(f"{data_dir}/AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt")
    func_map_dict = generate_workflows(parse_flat_workflow, parse_function_info, write_yamls, df)
    genreate_all_bench()
