import os
import threading
import time
from flask import Flask, request
from gevent.pywsgi import WSGIServer
# from main import main as __main__
import json
import socket
import subprocess
default_file = 'main.py'
work_dir = '/proxy'
work_dir = './'


class Runner:
    def __init__(self):
        self.code = None
        self.workflow = None
        self.function = None
        self.ctx = {}

    def init(self):
        print('init...')

        os.chdir(work_dir)

        # compile first
        filename = os.path.join(work_dir, default_file)
        print(f"filename={filename}")
        with open(filename, 'r') as f:
            self.code = compile(f.read(), filename, mode='exec')

        print('init finished...')

    def run(self, args):
        self.ctx = args
        # pre-exec
        exec(self.code, self.ctx)

        # run function
        start = time.time()
        out = eval('main()', self.ctx)
        end = time.time()

        return out

    def batch_run(self, req, responses):
        p = subprocess.Popen(["python3", "main.py"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        activate_SFS = req['azure_data'].get("activate_SFS", False)
        if activate_SFS:
            self.send_to_SFS_scheduler(
                pid=str(p.pid), function_id=req['function_id'])

        out_bytes, _ = p.communicate()
        # out_bytes = subprocess.check_output(["python3", "main.py"])
        result = out_bytes.decode('utf8').replace("'", '"')
        responses[req["function_id"]] = json.loads(result)
        # responses[req['function_id']] = __main__(req)
        print("INVOKING")

    def send_to_SFS_scheduler(self, pid: str, function_id: str):
        print(f"Now sending ({pid}, {function_id}) to SFS scheduler")
        data = {"pid": pid, "id": function_id}
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_data = json.dumps(data).encode("utf-8")
        udp_socket.sendto(bytes(send_data), ("172.18.0.1", 4009))
        udp_socket.close()


proxy = Flask(__name__)
proxy.status = 'new'
proxy.debug = False
runner = Runner()


@proxy.route('/status', methods=['GET'])
def status():
    res = {}
    res['status'] = proxy.status
    res['workdir'] = os.getcwd()
    if runner.function:
        res['function'] = runner.function
    return res


@proxy.route('/init', methods=['POST'])
def init():
    proxy.status = 'init'

    runner.init()

    proxy.status = 'ok'
    return ('OK', 200)


@proxy.route('/run', methods=['POST'])
def run():
    proxy.status = 'run'
    args = request.get_json(force=True, silent=True)
    # record the execution time
    start = time.time()
    runner.run(args=args)
    end = time.time()

    res = {
        "start_time": start,
        "end_time": end,
        "duration": end - start,
    }

    proxy.status = 'ok'
    return res


@proxy.route('/batch_run', methods=['POST'])
def batch_run():
    responses = {}
    proxy.status = 'run'
    reqs = request.get_json(force=True, silent=True)
    threads = []
    for req in reqs:
        # Identify the concurrency by myself
        req['concurrency'] = len(reqs)
        t = threading.Thread(target=runner.batch_run,
                             args=(req, responses))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    proxy.status = 'ok'
    return responses


if __name__ == '__main__':
    server = WSGIServer(('0.0.0.0', 5000), proxy)
    server.serve_forever()
