import glob
# Customize for Azure-bench

AZURE_BENCH_ADDR = '/home/vagrant/batching-request/benchmark/generator/azure-bench'
AZURE_WORKFLOWS_ADDR = f'{AZURE_BENCH_ADDR}/workflows'
AZURE_TRACE_ADDR = "/home/vagrant/data/Azure"
WORKFLOW_NAMES = list(map(lambda x:x.split("/")[-1], glob.glob(AZURE_WORKFLOWS_ADDR+"/*")))
AZURE_WORKFLOW_YAML_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}/flat_workflow.yaml" for name in WORKFLOW_NAMES}
AZURE_FUNCTION_INFO_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}" for name in WORKFLOW_NAMES}
AZURE_APPS = AZURE_WORKFLOW_YAML_ADDR.keys()