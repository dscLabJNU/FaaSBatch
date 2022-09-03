import gevent
import docker
import os
from function_info import parse
from function_group import FunctionGroup
from my_batching import Batching
from kraken import Kraken
from fifer import Fifer
from port_controller import PortController
from function import Function
import random
import sys
sys.path.append('../../config')
import config

repack_clean_interval = 5.000 # repack and clean every 5 seconds
dispatch_interval = 0.005 # 200 qps at most

# the class for scheduling functions' inter-operations
class FunctionManager:
    def __init__(self, config_path, min_port):
        self.function_info = parse(config_path)

        self.port_controller = PortController(min_port, min_port + 4999)
        self.client = docker.from_env()

        self.functions = {
            x.function_name: Function(self.client, x, self.port_controller)
            for x in self.function_info
        }

        self.init()
        self.init_func_groups()      
       
    def init_func_groups(self):
        """
        Record function groups and their belonging function instances.
        
        e.g.,
        function_groups: {
            "group_A": ["group_A_func_01", "group_A_func_02", ...],
            "group_B": ["group_B_func_01", ...]
        }
        """
        group_funcs_map = {}
        for function_name, function in self.functions.items():
            function_group = extract_group_name(func_name=function_name)

            if function_group not in group_funcs_map:
                group_funcs_map[function_group] = []
            group_funcs_map[function_group].append(function)
        
        group_instance = eval(config.STRATEGY)
        self.function_groups = {group_name: group_instance(name=group_name, functions=functions, 
                                                          docker_client=self.client, port_controller=self.port_controller)
                                for group_name, functions in group_funcs_map.items()}

    def init(self):
        print("Clearing previous containers.")
        os.system('docker rm -f $(docker ps -aq --filter label=workflow)')

        gevent.spawn_later(repack_clean_interval, self._clean_loop)
        gevent.spawn_later(dispatch_interval, self._dispatch_loop)
        
    def _clean_loop(self):
        gevent.spawn_later(repack_clean_interval, self._clean_loop)
        if config.REQUEST_BATCHING:
            for group in self.function_groups.values():
                gevent.spawn(group.repack_and_clean)
        else:        
            for function in self.functions.values():
                gevent.spawn(function.repack_and_clean)

    def _dispatch_loop(self):
        gevent.spawn_later(dispatch_interval, self._dispatch_loop)
        if config.REQUEST_BATCHING:
            for group in self.function_groups.values():
                gevent.spawn(group.dispatch_request)
        else:
            for function in self.functions.values():
                gevent.spawn(function.dispatch_request)
    
    def run(self, function_name, request_id, runtime, input, output, to, keys, duration=None):
        # print('run', function_name, request_id, runtime, input, output, to, keys)
        if function_name not in self.functions:
            print(f"There are functions {self.functions}")
            raise Exception(f"No such {function_name} function!")
        
        group_name = extract_group_name(func_name=function_name)
        if config.REQUEST_BATCHING:
            return self.function_groups[group_name].send_request(self.functions[function_name], request_id, runtime, input, output, to, keys, duration)
        else:
            return self.functions[function_name].send_request(request_id, runtime, input, output, to, keys)


def extract_group_name(func_name: str):
    return '_'.join(func_name.split('_')[:-1]) or func_name