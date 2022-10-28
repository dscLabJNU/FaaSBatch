import pandas as pd
import os
batching_path = "/home/vagrant/batching-request"
baseline_csv = f"{batching_path}/src/workflow_manager/tmp/latency_amplification_baseline.csv"
if not os.path.exists(baseline_csv):
    raise ValueError(
        "Cannot find baseline csv for caculating SLOs. Please executes baseline strategy according to the README.md")


df_baseline = pd.read_csv(baseline_csv)
groupby_func = df_baseline.groupby("function")
func_SLOs = {}
for func, info in groupby_func:
    func_SLOs[func] = info['duration(ms)'].quantile(0.98)