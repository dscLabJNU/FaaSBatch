import os
import threading
import importlib
import time
from flask import Flask, request
from gevent.pywsgi import WSGIServer
from main import main as __main__
import aspectlib
import boto3
from local_cache import LocalCache
import const
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
# Storing the key set of 'None' output
unavialble_key = []
cached_keys = set()


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

    start = time.time()
    # Normal exeuction
    result = yield aspectlib.Proceed
    duration = time.time() - start

    if result:
        cached_keys.add(hash_args)
        result_cache.set(hash_args, {r'result': result,
                                     r'creation_time': duration})
    else:
        unavialble_key.append(hash_args)
    yield aspectlib.Return(result)


@proxy.route('/cache_info', methods=['GET'])
def cache_info():
    """
    Search and return the cache information (hits, invos, and hit rate)
    """
    return result_cache.cache_info()


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


def set_cache_strategy(cache_strategy, cache_size=const.DEFAULT_CACHE_MAXLEN):
    global result_cache

    cur_cache_strategy = os.environ.get("cache_strategy")
    cur_cache_size = os.environ.get("cache_size")
    if cache_strategy == cur_cache_strategy and str(cache_size) == cur_cache_size:
        # No need to reset
        return
    os.environ["cache_strategy"] = cache_strategy
    os.environ['cache_size'] = str(cache_size)
    logger.info(f"Setting cache strategy to {cache_strategy}")
    # Dynamically import the module
    module = importlib.import_module('eviction_strategy')
    # Get the reference to the class from the module
    class_ref = getattr(module, cache_strategy)
    print(f"cache_size: {cache_size}")
    result_cache = LocalCache(class_ref(maxlen=cache_size))


@proxy.route('/set_strategy', methods=['POST'])
def set_strategy():
    args = request.get_json(force=True, silent=True)
    cache_strategy = args.get("cache_strategy", "InfiniteCache")
    cache_size = args.get("cache_size", const.DEFAULT_CACHE_MAXLEN)
    print(f"cache_size: {cache_size}")
    set_cache_strategy(cache_strategy=cache_strategy, cache_size=cache_size)
    return {'OK': 200}


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
    logger.debug(f"{len(cached_keys)} of keys are cached")
    return responses


@proxy.route('/num_of_cache_keys', methods=['GET'])
def get_num_of_cache_keys():
    return {"num_of_cache_keys": len(cached_keys)}


if __name__ == '__main__':
    server = WSGIServer(('0.0.0.0', 5000), proxy)
    set_cache_strategy(cache_strategy="InfiniteCache")
    server.serve_forever()
