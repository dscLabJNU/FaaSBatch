import threading
import time
import json
import os
import sys
from datetime import datetime

def timer(sleep_time):
    # sleep 
    time.sleep(int(sleep_time)/1000)
    os._exit(1)

def fib(n):
    if n<0:
        print("Incorrect input")
    # First Fibonacci number is 0 
    elif n==1:
        return 0
    # Second Fibonacci number is 1 
    elif n==2:
        return 1
    else:
        return fib(n-1)+fib(n-2)

def main(args):
    # os.system(f"taskset -c -p {os.getpid()}")
    # print(f"My pid is {os.getpid()}")
    start = time.time()
    if len(sys.argv) > 1:
        n = sys.argv[1]
    else:
        n = 30
    result = fib(int(n))
    end = time.time()
    return {
            "exec_time":(end - start) * 1000, # Converts s to ms
            "start_time":start,
            "end_time":end,
            "result": result}

print(json.dumps(main({})), end="")
