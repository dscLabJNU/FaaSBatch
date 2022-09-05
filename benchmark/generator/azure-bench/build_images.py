import os
import yaml
import glob


def parse_function_info(workflow_path):
    function_info = yaml.load(
        open(f'{workflow_path}/function_info.yaml'), yaml.FullLoader)
    return function_info


workflow_paths = glob.glob("./workflows/*")
for workflow_path in workflow_paths:
    function_info = parse_function_info(workflow_path)
    rm_images = 'docker rmi -f $(docker images -f "reference=azure_bench_func*" --format "{{.ID}}")'
    os.system(rm_images)
    # build images
    functions = list(map(lambda x: x, function_info['functions']))
    for function in functions:
        print('------building image for function ' +
              function['name'] + '------')
        os.system('docker build -t ' +
                  function['name'] + ' ../../../src/azure_container/')
