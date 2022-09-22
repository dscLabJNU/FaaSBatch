import os
import threading
import time
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from main import main as __main__
import aspectlib
import boto3

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
        # self.ctx = req
        # pre-exec
        # exec(self.code, self.ctx)
        
        # run function
        with aspectlib.weave(boto3.Session, open_hook):
            responses[req['function_id']] = __main__(req)
            # responses[req['request_id']] = eval('main()', self.ctx)
        print("INVOKING")
        # return {"request_id": req['request_id'], "out": __main__(req)}


proxy = Flask(__name__)
proxy.status = 'new'
proxy.debug = False
runner = Runner()

result_dict = {}
@aspectlib.Aspect
def open_hook(*args, **kwargs):
    """
        The hash value of all input parameters as KEY,
        and the output of the monitored function as VALUE.
        The {KEY: VALUE} relationship is maintained by `result_dict`
    """
    # yield aspectlib.Return(s3)
    combind_inputs = (args, tuple(sorted(kwargs.items())))
    hash_args = hash(str(combind_inputs))
    print(f"hash_args: {hash_args}")
    if hash_args in result_dict:
        print(f'cached result is {result_dict[hash_args]}')
        yield aspectlib.Return(result_dict[hash_args])

    result = yield aspectlib.Proceed

    result_dict[hash_args] = result
    print(f"the result is: {result}")
    print(f"type of the result: {type(result)}")
    yield aspectlib.Return(result)


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
    # Identify the concurrency by myself
    for req in reqs:
        req['concurrency'] = len(reqs)

    # trigger socket client cache
    first_req = reqs.pop(0)
    runner.batch_run(first_req, responses)
    
    for req in reqs:
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
