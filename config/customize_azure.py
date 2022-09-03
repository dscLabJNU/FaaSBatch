import glob
# Customize for Azure-bench

BEHCKMARK_BASE = '/home/vagrant/batching-request/benchmark'
AZURE_WORKFLOWS_ADDR = f'{BEHCKMARK_BASE}/generator/azure-bench/workflows'
WORKFLOW_NAMES = list(map(lambda x:x.split("/")[-1], glob.glob(AZURE_WORKFLOWS_ADDR+"/*")))
AZURE_WORKFLOW_YAML_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}/flat_workflow.yaml" for name in WORKFLOW_NAMES}