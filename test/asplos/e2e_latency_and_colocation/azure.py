import pandas as pd
import customize_azure
import json


class Azure:
    def __init__(self, workflow_info, azure_type) -> None:
        self.info = workflow_info
        self.azure_type = azure_type
        self.df = self.load_df(day=self.info['azure_trace_day'])

    def load_df(self, day):
        print("Loading Azure dataset...")
        df = pd.read_csv(
            f"{customize_azure.AZURE_TRACE_ADDR}/AzureFunctionsInvocationTraceForTwoWeeksJan2021Day{day:02d}.csv")
        df['start_timestamp'] = df['end_timestamp'] - df['duration']
        print(df['invo_ts'])
        return df

    def load_mappers(self):
        with open(f"{customize_azure.AZURE_WORKFLOWS_ADDRS[self.azure_type]}/func_mapper.json") as load_f:
            func_map_dict = json.load(load_f)
        with open(f"{customize_azure.AZURE_WORKFLOWS_ADDRS[self.azure_type]}/app_mapper.json") as load_f:
            app_map_dict = json.load(load_f)

        return func_map_dict, app_map_dict

    def filter_df(self, app_map_dict):
        if not self.info['workflow_names']:
            raise ValueError(
                "There are no app to be filtered, please check your configuration")
        df = self.df
        azure_apps = self.info['workflow_names']
        start = self.info['time_line_start']
        end = self.info['time_line_end']
        # 筛选出指定的 app
        print(f"Filtering apps: {azure_apps}")
        df = df[pd.Series(
            list(map(lambda x: '_'.join(app_map_dict[x].split("_")[:4]), df['app']))).isin(azure_apps)]
        if df['app'].nunique() != len(azure_apps):
            raise ValueError(
                "The number of apps before and after filtering is not equal")

        # 筛选出指定的 time-line
        print(f"Filtering data from {start} to {end}")
        filter_df = df[(df['invo_ts'] >= start) &
                       (df['invo_ts'] <= end)].copy()

        # 调整invo_ts的偏移量，从0开始
        filter_df['invo_ts'] = pd.to_datetime(filter_df['invo_ts'], utc=True)
        filter_df['invo_ts'] = filter_df['invo_ts'] - \
            pd.to_datetime(start, utc=True)
        print(
            f"We have {filter_df['app'].nunique()} of unique apps, {filter_df['func'].nunique()} of unique functions, and {filter_df['invo_ts'].count()} of invocations")

        return filter_df
