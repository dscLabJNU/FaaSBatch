### I/O optimize container runtime
This folder contians I/O optimize runtime.

### Overview
For memorizing I/O clients (S3 client), we implement a cache pool (`local_cache.py`) and leverage some eviction straties (in `evication_strategy.py`) to schedule the instances.

Several eviction strategies are included, such as LFU, LRU and so on.

The cache pool works during the I/O client creation, where the creation is monitored by using `aspectlib.weave` in `proxy.py`

### Evaluation
```shell
bash build_image.sh # to build the container image named `boto3-client-optimize`

```
