import glob
import json
import os
# Customize for Azure-bench

# ======= NEED TO CONFIG =======
AZURE_TRACE_ADDR = "/data/data1/jairwu/data/Azure"
# ======= NEED TO CONFIG =======


PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AZURE_BENCH_ADDR = f"{PROJECT_PATH}/benchmark/generator/azure-bench"
AZURE_WORKFLOWS_ADDRS = {
    "cpu_optimize": f'{AZURE_BENCH_ADDR}/cpu_workflows/optimize',
    "cpu_native": f'{AZURE_BENCH_ADDR}/cpu_workflows/native',
    "io_native": f'{AZURE_BENCH_ADDR}/io_workflows/native',
    "io_optimize": f'{AZURE_BENCH_ADDR}/io_workflows/optimize',
}

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