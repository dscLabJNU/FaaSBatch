from enum import IntEnum, auto
import hashlib

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

def hash_string(s: str):
    sha1 = hashlib.sha1()
    sha1.update(s.encode('utf-8'))
    return sha1.hexdigest()