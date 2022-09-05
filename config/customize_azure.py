import glob
# Customize for Azure-bench

BEHCKMARK_BASE = '/home/vagrant/batching-request/benchmark'
AZURE_WORKFLOWS_ADDR = f'{BEHCKMARK_BASE}/generator/azure-bench/workflows'
TIME_LINE_START = "2021-02-01 14:00:00+00:00"
TIME_LINE_END = "2021-02-01 14:15:00+00:00"
WORKFLOW_NAMES = list(map(lambda x:x.split("/")[-1], glob.glob(AZURE_WORKFLOWS_ADDR+"/*")))
AZURE_WORKFLOW_YAML_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}/flat_workflow.yaml" for name in WORKFLOW_NAMES}
AZURE_FUNCTION_INFO_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}" for name in WORKFLOW_NAMES}
AZURE_APPS = AZURE_WORKFLOW_YAML_ADDR.keys()