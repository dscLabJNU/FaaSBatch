import glob
import os
# Customize for Azure-bench

AZURE_BENCH_ADDR = '/home/vagrant/batching-request/benchmark/generator/azure-bench'
# Indicate the workflow you want to run
WORKFLOW_INDICATOR = os.environ.get("azure_type", "cpu_native")
AZURE_WORKFLOWS_ADDRS = {
    "cpu_native": f'{AZURE_BENCH_ADDR}/cpu_workflows/native',
    "io_native": f'{AZURE_BENCH_ADDR}/io_workflows/native',
    "io_optimize": f'{AZURE_BENCH_ADDR}/io_workflows/optimize',
}
AZURE_WORKFLOWS_ADDR = f'{AZURE_WORKFLOWS_ADDRS[WORKFLOW_INDICATOR]}'
AZURE_TRACE_ADDR = "/home/vagrant/data/Azure"
WORKFLOW_NAMES = list(map(lambda x:x.split("/")[-1], glob.glob(AZURE_WORKFLOWS_ADDR+"/azure_bench_app*")))
AZURE_WORKFLOW_YAML_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}/flat_workflow.yaml" for name in WORKFLOW_NAMES}
AZURE_FUNCTION_INFO_ADDR = {name: f"{AZURE_WORKFLOWS_ADDR}/{name}" for name in WORKFLOW_NAMES}
AZURE_APPS = AZURE_WORKFLOW_YAML_ADDR.keys()