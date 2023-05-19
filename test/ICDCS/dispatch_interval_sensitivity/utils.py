from enum import IntEnum, auto


class SamplingMode(auto):
    Sequantial = "sequential"
    Uniform = "uniform"


class AzureTraceSlecter(auto):
    # See element index on workflow_infos.yaml
    AzureFunction = 0
    AzureBlob = 1


class AzureType(auto):
    CPU = 'cpu'
    IO = 'io'
