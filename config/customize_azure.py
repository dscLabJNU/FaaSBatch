import glob
import json
# Customize for Azure-bench

AZURE_BENCH_ADDR = '/home/vagrant/batching-request/benchmark/generator/azure-bench'
AZURE_WORKFLOWS_ADDRS = {
    "cpu_optimize": f'{AZURE_BENCH_ADDR}/cpu_workflows/optimize',
    "cpu_native": f'{AZURE_BENCH_ADDR}/cpu_workflows/native',
    "io_native": f'{AZURE_BENCH_ADDR}/io_workflows/native',
    "io_optimize": f'{AZURE_BENCH_ADDR}/io_workflows/optimize',
}
AZURE_TRACE_ADDR = "/home/vagrant/data/Azure"

WORKFLOW_NAMES = []
AZURE_WORKFLOW_YAML_ADDR = {}
AZURE_FUNCTION_INFO_ADDR = {}
for TYPE, ADDR in AZURE_WORKFLOWS_ADDRS.items():
    WORKFLOW_NAMES.extend(list(map(lambda x:x.split("/")[-1], glob.glob(ADDR+"/azure_bench_app*"))))
    AZURE_WORKFLOW_YAML_ADDR.update({name: f"{ADDR}/{name}/flat_workflow.yaml" for name in WORKFLOW_NAMES if TYPE in name})
    AZURE_FUNCTION_INFO_ADDR.update({name: f"{ADDR}/{name}" for name in WORKFLOW_NAMES if TYPE in name})

AZURE_APPS = AZURE_WORKFLOW_YAML_ADDR.keys()
# For explicit checking,
# with open(f"./AZURE_FUNCTION_INFO_ADDR.json", 'w') as dump_f:
#     dump_f.write(json.dumps(AZURE_FUNCTION_INFO_ADDR))
# with open(f"./AZURE_WORKFLOW_YAML_ADDR.json", 'w') as dump_f:
#     dump_f.write(json.dumps(AZURE_WORKFLOW_YAML_ADDR))