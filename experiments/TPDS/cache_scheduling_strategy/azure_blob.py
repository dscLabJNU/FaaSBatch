import logging
import random
import pandas as pd
import math
import customize_azure
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import hashlib
import os
from utils import SamplingMode


class AzureBlob:
    def __init__(self, workflow_info, azure_type) -> None:
        self.info = workflow_info
        self.azure_type = azure_type
        self.df = self.load_df(day=self.info['azure_trace_day'])

    def load_df(self, day):
        print("Loading Azure Blob dataset...")
        # TODO delete the nrow limit
        df = pd.read_csv(
            f"{customize_azure.AZURE_TRACE_ADDR}/AzureFunctionBlobAccessTrace/azurefunctions-accesses-2020-day{day:02d}.csv", nrows=30000)
        return df

    def load_mappers(self):
        with open(f"{customize_azure.AZURE_WORKFLOWS_ADDRS[self.azure_type]}/func_mapper.json") as load_f:
            func_map_dict = json.load(load_f)
        with open(f"{customize_azure.AZURE_WORKFLOWS_ADDRS[self.azure_type]}/app_mapper.json") as load_f:
            app_map_dict = json.load(load_f)

        return func_map_dict, app_map_dict

    def plot_RPS(self, df: pd.DataFrame):
        plt.rc('font', family='Times New Roman', weight='bold', size=10)
        os.system("mkdir -p imgs")
        timeline = "S"
        df['invo_ts'] = df['invo_ts'] + \
            pd.to_datetime(self.info['time_line_start'], utc=True)
        df['invo_ts'] = pd.to_datetime(df['invo_ts'])
        values = df.resample(timeline, on='invo_ts').count()[
            'AnonFunctionInvocationId']
        values = values[values != 0]
        fig, ax = plt.subplots(figsize=(5, 1.5))
        x_list = values.index

        xformatter = mdates.DateFormatter('%H:%M:%S')
        ax.xaxis.set_major_formatter(xformatter)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(6))
        # ax.set_xlabel(f"Timeline (Day{day:02d})")
        ax.set_ylabel("Concurrency", weight='bold')
        ax.set_xlabel("Timeline", weight='bold')
        ax.plot(x_list, values, lw=2)
        # plt.xticks(fontsize=8)
        fig.savefig("imgs/AzureBlobWorkloadRPS.pdf", bbox_inches='tight')

    def filter_by_freq(self, threshold=10):
        df = self.df

        df['aws_boto3'] = (
            df['AnonUserId'].astype(str) + "_key_id," +
            df['AnonUserId'].astype(str) + "_access_key," +
            df['AnonRegion'].astype(str) + "," +
            df['AnonBlobName'].astype(str) + df['AnonBlobETag'].astype(str) + "_name," +
            df['AnonBlobName'].astype(str) + df['AnonBlobETag'].astype(str) + "_key," +
            df['Read'].astype(str)
        )
        # 使用 SHA-1 计算 aws_boto3 的 hash 值
        df['aws_boto3_hash'] = df['aws_boto3'].apply(
            lambda x: hashlib.sha1(x.encode()).hexdigest())
        # 首先计算每个哈希值的频次
        hash_frequency = df['aws_boto3_hash'].value_counts()

        # 找到访问频次大于阈值的哈希值
        filtered_hashes = hash_frequency[hash_frequency > threshold].index

        # 筛选 df 中的行，其 aws_boto3_hash 值在 filtered_hashes 中
        filtered_df = df[df['aws_boto3_hash'].isin(filtered_hashes)]

        # Clear the temporary columns
        filtered_df = filtered_df.drop(columns=['aws_boto3_hash', 'aws_boto3'])

        self.df = filtered_df

    def filter_df(self, app_map_dict=None, num_invos=None, mode=SamplingMode.Sequantial):
        """
        mode:
            sequential (default): Starting from the lowest index, select ${num_invos} elements in order.
            uniform: Perform uniform random sampling of ${num_invos} elements from the sequence.
        """
        # We want to test the hot data???
        # self.filter_by_freq()

        df = self.df
        start = self.info['time_line_start']
        end = self.info['time_line_end']

        # 筛选出指定的 time-line
        print(f"Filtering data from {start} to {end}")
        filter_df = df[(df['Datetime'] >= start) &
                       (df['Datetime'] <= end)].copy()

        # 调整invo_ts的偏移量，从0开始
        filter_df['invo_ts'] = pd.to_datetime(
            filter_df['Datetime']) - pd.to_datetime(start)

        num_invos = min(num_invos, len(filter_df))
        # Picks top $(num_invos) of the filter_df for benchmarking
        if num_invos:
            if mode == SamplingMode.Sequantial:
                filter_df = filter_df[:num_invos]
            elif mode == SamplingMode.Uniform:
                filter_df = filter_df.sample(n=num_invos, random_state=5432)
        print(
            f"We have {filter_df['AnonAppName'].nunique()} of unique apps, {filter_df['AnonBlobName'].nunique()} of unique blobs, and {filter_df['invo_ts'].count()} of invocations")
        return filter_df.reset_index().drop('index', axis=1)
