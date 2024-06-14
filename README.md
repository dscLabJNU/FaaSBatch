# FaaSBatch


## Introduction

FaaSBatch is a serverless workflow engine that enables efficient workflow execution, it batches the concurrency function invocation into an identical group and executes them in parallel inside a container. Also, FaaSBatch reuses the redundant resource incurred inside a container.

FaaSBatch is developed based on the [FaaSFlow](https://github.com/lzjzx1122/FaaSFlow) framework.

## Hardware Dependencies and Private IP Address

1. In our experiment setup, we use two Virtual Machines (VMs): a small client VM with 8 vCPUs and 16 GB memory and a large worker VM with 32 vCPUs and 64 GB memory. 

2. IP addresses of our VMs are following, please replace them according to your setup
   ```shell
    worker IP: 10.0.0.101
    client IP: 10.0.0.103
   ```
3. Python version: 3.9, creating a virtual python enviornment by using minoconda/anaconda is recommended

## About Config Setting

There are 3 places for config setting. 
1. `./config/config.py`: reset the client IP (MASTER_IP), path to the SFS (SFSPATH) and path to the resource monitor (RESOURCE_MONITOR) 
2. `./config/customize_azure.py`: reset the Azure dataset path (AZURE_TRACE_ADDR)
3. `./src/grouping/node_info.yaml`: reset the worker IPs

## Installation and Software Dependencies

Clone our code `https://github.com/GitHubDiom/batching-request.git` and:

1. Reset `worker_address` configuration with your <worker_ip>:8000 on `src/grouping/node_info.yaml`.

2. The `scale_limit` parameter is used in original FaaSFlow, so just ignore it.

3. Reset `COUCHDB_URL` as `http://openwhisk:openwhisk@<master_ip>:5984/`  in `config/config.py`, `src/container/container_config.py`. It will specify the corresponding database storage you built previously.

4. Then, apply all the modification into each node.

5. To make sure the python dependencies are well installed, run `pip3 install -r requirements.txt` in `~/batching-request/scripts`.

6. On the storage node: Run `bash scripts/db_setup.bash`. It installs docker, CouchDB, some python packages, and build grouping results from the Azure benchmark. For the remaining dev, one can restart the cluster by running `bash scripts/db_restart.bash`.
    
7. On worker node: Run `bash scripts/worker_setup.bash`. This installs docker, Redis, some python packages, and build docker images from the Azure benchmark. Similarly, `bash scripts/worker_restart.sh` restarts the worker, it regenerates Azure trace, rebuilds the container images.

8. Ensure SSH login communication (without password) is possible between the machines used for the experiment


## Run Experiment

We provide some test scripts under `test/ICDCS`.
**Note:** We recommend to restart all `proxy.py` and `gateway.py` processes whenever you start the `run.py` script, to avoid any potential bug. The restart will clear all background function containers and reclaim the memory space. 

### Dispatch Interval Sensitivity
In client node, run the following command to start the experiment varying the `dispath_interval` from 0.01 to 0.5.


```shell
cd ./test/ICDCS/dispatch_interval_sensitivity
bash run_all.sh

# It stops all the experiment in any time
bash stop_all.sh
```

After that, all experimental results are stored in `results` folder.

## Experimental Results
Just ignore the `amplication` in `latency_amplification`, this is a type mistake, and it actually shows the different types of latencies (scheduling_latency, cold_start latency, execution_latency, and queue_latency, also memory inside a container).

For each of type of function (CPU and I/O), the corresponding result folders container the plot scripts (`plot_latency.ipynb`, `plot_provisioned_container.ipynb`, and `plot_utilization.ipynb`)

## Cite
```bibTex
@ARTICLE{wu2024FaaSBatch,
  author={Wu, Zhaorui and Deng, Yuhui and Zhou, Yi and Li, Jie and Pang, Shujie and Qin, Xiao},
  journal={IEEE Transactions on Computers}, 
  title={FaaSBatch: Boosting Serverless Efficiency With In-Container Parallelism and Resource Multiplexing}, 
  year={2024},
  volume={73},
  number={4},
  pages={1071-1085},
  doi={10.1109/TC.2024.3352834
}

```
