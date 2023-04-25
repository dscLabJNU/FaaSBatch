import pandas as pd
import os
batching_path = "/home/vagrant/batching-request"
baseline_csv = f"{batching_path}/src/workflow_manager/tmp/latency_amplification_BaseBatching.csv"
if not os.path.exists(baseline_csv):
    raise ValueError(
        "Cannot find baseline csv for caculating SLOs. Please executes baseline strategy according to the README.md")


df_baseline = pd.read_csv(baseline_csv)
groupby_func = df_baseline.groupby("function")
func_SLOs = {}
SLO_quantail=float(os.environ.get("SLO_quantail", 0.98))
for func, info in groupby_func:
    # schedule_time includs cold start, and time overhead of the strategy
    func_SLOs[func] = (info['exec_time(ms)'] + info['schedule_time(ms)']).quantile(SLO_quantail)