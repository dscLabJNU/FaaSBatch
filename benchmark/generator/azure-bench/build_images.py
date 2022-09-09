import os
import yaml
import glob


def parse_function_info(workflow_path):
    function_info = yaml.load(
        open(f'{workflow_path}/function_info.yaml'), yaml.FullLoader)
    return function_info


workflow_paths = glob.glob("./workflows/*")
rm_containers = 'docker rm -f $(docker ps -aq --filter label=workflow)'
rm_images = 'docker rmi -f $(docker images -f "reference=azure_bench_func*" --format "{{.ID}}")'
rm_dangling_images = 'docker rmi -f $(docker images -q -a -f dangling=true)'
os.system(rm_dangling_images)
os.system(rm_containers)
os.system(rm_images)
for workflow_path in workflow_paths:
    function_info = parse_function_info(workflow_path)
    # build images
    functions = list(map(lambda x: x, function_info['functions']))
    for function in functions:
        print('------building image for function ' +
              function['name'] + '------')
        os.system('docker build -t ' +
                  function['name'] + ' ../../../src/azure_container/')
