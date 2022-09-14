import os
import threading
import time
import couchdb
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from Store import Store
import container_config
import redis
from main import main as __main__

default_file = 'main.py'
work_dir = '/proxy'
couchdb_url = container_config.COUCHDB_URL
db_server = couchdb.Server(couchdb_url)
redis_server = redis.StrictRedis(host=container_config.REDIS_HOST, port=container_config.REDIS_PORT, db=container_config.REDIS_DB)
latency_db = db_server['workflow_latency']

class Runner:
    def __init__(self):
        self.code = None
        self.workflow = None
        self.function = None
        self.ctx = {}

    def init(self, workflow, function):
        print('init...')

        # update function status
        self.workflow = workflow
        self.function = function

        os.chdir(work_dir)

        # compile first
        filename = os.path.join(work_dir, default_file)
        with open(filename, 'r') as f:
            self.code = compile(f.read(), filename, mode='exec')

        print('init finished...')

    def run(self, request_id, runtime, input, output, to, keys):
        # FaaSStore
        store = Store(self.workflow, self.function, request_id, input, output, to, keys, runtime, db_server, redis_server)
        self.ctx = {'workflow': self.workflow, 'function': self.function, 'store': store}

        # pre-exec
        exec(self.code, self.ctx)

        # run function
        start = time.time()
        out = eval('main()', self.ctx)
        end = time.time()

        latency_db.save({'request_id': request_id, 'function_name': self.function, 'phase': 'edge+node', 'time': end - start})
        return out


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

    inp = request.get_json(force=True, silent=True)
    runner.init(inp['workflow'], inp['function'])

    proxy.status = 'ok'
    return ('OK', 200)


@proxy.route('/run', methods=['POST'])
def run():
    proxy.status = 'run'

    inp = request.get_json(force=True, silent=True)
    request_id = inp['request_id']
    runtime = inp['runtime']
    input = inp['input']
    output = inp['output']
    to = inp['to']
    keys = inp['keys']

    # record the execution time
    start = time.time()
    runner.run(request_id, runtime, input, output, to, keys)
    end = time.time()

    res = {
        "start_time": start,
        "end_time": end,
        "duration": end - start,
        "inp": inp
    }

    proxy.status = 'ok'
    return res

@proxy.route('/batch_run', methods=['POST'])
def batch_run():
    proxy.status = 'run'
    inps = request.get_json(force=True, silent=True)
    responses = {}
    threads = []
    for inp in inps:
        t = threading.Thread(target=run_single, args=(inp, responses,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
    proxy.status = 'ok'
    return responses

def run_single(inp, responses):
    request_id = inp['request_id']
    runtime = inp['runtime']
    input = inp['input']
    output = inp['output']
    to = inp['to']
    keys = inp['keys']
    function_id = inp['function_id']

    # record the execution time
    start = time.time()
    runner.run(request_id, runtime, input, output, to, keys)
    end = time.time()

    responses[function_id] = {
        "start_time": start,
        "end_time": end,
        "duration": end - start,
        "inp": inp
    }
    

if __name__ == '__main__':
    server = WSGIServer(('0.0.0.0', 5000), proxy)
    server.serve_forever()
