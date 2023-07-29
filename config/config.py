import os
import customize_azure

# ======= NEED TO CONFIG =======
MASTER_IP = "192.168.1.18"
SFSPATH = "/home/jairwu/go/src/SFS-batching-requests"
RESOURCE_MONITOR = "/home/jairwu/resource/FaaS/openwhisk-resource-monitor"
# ======= NEED TO CONFIG =======


PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUCHDB_URL = f'http://openwhisk:openwhisk@{MASTER_IP}:5984/'
REDIS_HOST = '127.0.0.1' # it serves to connect with the local redis, so it should be 127.0.0.1
REDIS_PORT = 6379 # it follows the same configuration as created redis by docker (e.g., -p 6379:6379)
REDIS_DB = 0
GATEWAY_ADDR = f'{MASTER_IP}:7000'  # need to update as your private_ip
MASTER_HOST = f'{MASTER_IP}:8000'  # need to update as your private_ip
WORKFLOW_YAML_ADDR = {}
WORKFLOW_YAML_ADDR.update(customize_azure.AZURE_WORKFLOW_YAML_ADDR)

# ====== None of our FaaSBatch business ======
NETWORK_BANDWIDTH = 25 * 1024 * 1024 / 4  # 25MB/s / 4
NET_MEM_BANDWIDTH_RATIO = 15  # mem_time = net_time / 15
CONTAINER_MEM = 256 * 1024 * 1024  # 256MB
NODE_MEM = 256 * 1024 * 1024 * 1024  # 256G
RESERVED_MEM_PERCENTAGE = 0.2
GROUP_LIMIT = 100
DATA_MODE = 'raw'  # raw, optimized
CONTROL_MODE = 'WorkerSP'  # WorkerSP, MasterSP
CLEAR_DB_AND_MEM = True
# ====== None of our FaaSBatch business ======

FUNCTION_INFO_ADDRS = {}
FUNCTION_INFO_ADDRS.update(customize_azure.AZURE_FUNCTION_INFO_ADDR)
REQUEST_BATCHING = os.environ.get("request_batching", "True") == 'True'
STRATEGY = os.environ.get("strategy", "FaaSBatch") # BaseBatching, FaaSBatch, SFS, Kraken
DISPATCH_INTERVAL = float(os.environ.get("dispatch_interval", 0.2))
"""We first evaluates benchmark functions in baseline stragety (spawn a single container to serve each incoming request)
and then calculates the 98th latency as the corresponding SLO
"""
if os.environ.get("strategy") == "Kraken":
    import calculate_SLOs
    FUNCTION_SLOS = calculate_SLOs.func_SLOs
    SLO_quantail = calculate_SLOs.SLO_quantail
