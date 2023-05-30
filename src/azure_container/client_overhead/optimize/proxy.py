import os
import threading
import const
import time
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from main import main as __main__
import aspectlib
import boto3
from local_cache import LocalCache
import eviction_strategy
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
        logger.info('init...')

        os.chdir(work_dir)

        # compile first
        filename = os.path.join(work_dir, default_file)
        logger.info(f"filename={filename}")
        with open(filename, 'r') as f:
            self.code = compile(f.read(), filename, mode='exec')

        logger.info('init finished...')

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
        # run function
        with aspectlib.weave(boto3.Session, open_hook):
            responses[req['function_id']] = __main__(req)


proxy = Flask(__name__)
proxy.status = 'new'
proxy.debug = False
runner = Runner()
result_cache = {}
# For caching the instance in container
result_cache = LocalCache(eviction_strategy.LRU())
# Storing the key set of 'None' output
unavialble_key = []


@aspectlib.Aspect
def open_hook(*args, **kwargs):
    """
        The hash value of all input parameters as KEY,
        and the output of the monitored function as VALUE.
        The {KEY: VALUE} relationship is maintained by `result_cache`
    """
    combind_inputs = (args, tuple(sorted(kwargs.items())))
    hash_args = hash(str(combind_inputs))
    if hash_args not in unavialble_key:
        # There are some None input to generate None ouput
        result = result_cache.get(hash_args)
        if result is not LocalCache.notFound:
            yield aspectlib.Return(result)

    # Normal exeuction
    result = yield aspectlib.Proceed

    if result:
        result_cache.set(hash_args, {r'result': result,
                                     r'expire': LocalCache.nowTime() + const.DEFAULT_CACHE_LEASE})
    else:
        unavialble_key.append(hash_args)
    yield aspectlib.Return(result)


@proxy.route('/hit_rate', methods=['GET'])
def get_hit_rate():
    """
    Search and return the cache hit rate
    """
    hit_rate = result_cache.get_hit_rate()
    return {"hit_rate": hit_rate}


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
