import os
import yaml
import glob


def parse_function_info(workflow_path):
    function_info = yaml.load(
        open(f'{workflow_path}/function_info.yaml'), yaml.FullLoader)
    return function_info


def get_workflow_type(workflow_path):
    types = ['io', 'cpu']
    for t in types:
        if t in workflow_path:
            return t


def get_dockerfile_dir(workflow_type, m):
    cpu_dockerfile = "../../../src/azure_container"
    if workflow_type == 'io':
        method = m.split("/")[-1]
        return f"{cpu_dockerfile}/client_overhead/{method}"
    elif workflow_type == 'cpu':
        return cpu_dockerfile


workflow_paths = glob.glob("./*workflows")
rm_containers = 'docker rm -f $(docker ps -aq --filter label=workflow)'
rm_images = 'docker rmi -f $(docker images -f "reference=azure_*_func*" --format "{{.ID}}")'
rm_dangling_images = 'docker rmi -f $(docker images -q -a -f dangling=true)'
os.system(rm_dangling_images)
os.system(rm_containers)
os.system(rm_images)
for workflow_path in workflow_paths:
    workflow_type = get_workflow_type(workflow_path)
    
    methods = glob.glob(f"{workflow_path}/*")
    for m in methods:
        dockerfile_dir = get_dockerfile_dir(workflow_type, m)
        workflows = glob.glob(f"{m}/azure_bench*")
        for workflow in workflows:
            function_info = parse_function_info(workflow)
            # build images
            functions = list(map(lambda x: x, function_info['functions']))
            
            for function in functions:
                print(f"docker build -t {function['name']} {dockerfile_dir}")
                os.system(f"docker build -t {function['name']} {dockerfile_dir}")
