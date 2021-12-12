#!/usr/bin/env python3
import logging
import concurrent.futures
import itertools
import multiprocessing
from concurrent.futures.process import ProcessPoolExecutor
from functools import lru_cache
from multiprocessing.queues import JoinableQueue

logger = logging.getLogger("WorkersPool")


def _custom_cpu_count(*args, **kwargs):
    return 1


try:
    from concurrent.futures.thread import ThreadPoolExecutor
except ImportError:
    ThreadPoolExecutor = None
try:
    from multiprocessing import Pool, cpu_count
except ImportError:
    Pool = None
    cpu_count = lambda: 1  #
try:
    from multiprocessing.pool import ThreadPool
except ImportError:
    ThreadPool = None
try:
    from gevent.threadpool import ThreadPoolExecutor as GreenThreadPool
except ImportError:
    GreenThreadPool = None

DEFAULT_WORKERS = 3


class MultiProcessPipeline:
    def __init__(self, funcs, collection, default_process_num=1):
        self.collection = collection
        # communication queues
        self.queues = [JoinableQueue(maxsize=-1, ctx=multiprocessing.get_context()) for _ in range(len(funcs) + 1)]

        first_func, start_size, current_size = None, 0, 0

        self.processes = []
        for idx, data in enumerate(funcs):
            current_func, current_size = self.get_current_info(data, default_process_num)
            next_func, next_size = self.get_next_info(funcs, idx, default_process_num)

            assert callable(current_func), f"Function '{current_func}' is not a callable"

            readq, writeq = self.queues[idx], self.queues[idx + 1]
            barrier = multiprocessing.Barrier(current_size)
            start_size = start_size or max(1, current_size)
            first_func = first_func or current_func

            self.processes.append(
                [
                    MultiProcessPipeline.Consumer(readq, writeq, barrier, num_stops, next_func)
                    for i, num_stops in enumerate(self.get_num_stops(current_size, next_size))
                ]
            )

        self.end_size = current_size
        self.start_size = start_size
        self.start_func = first_func

    @staticmethod
    def get_current_info(data, default_process_num):
        if isinstance(data, tuple):
            current_func, current_size = data
        else:
            current_func, current_size = data, default_process_num
        return current_func, current_size

    @staticmethod
    def get_next_info(funcs, idx, default_process_num):
        try:
            next_func, next_size = funcs[idx + 1]
        except TypeError:
            next_func, next_size = (funcs[idx + 1], default_process_num)
        except IndexError:
            next_func, next_size = None, None
        return next_func, next_size

    def __call__(self, *args, ignore_results=False, **kwargs):
        self.start()
        self.join(ignore_results=ignore_results)

    def start(self):
        for p in itertools.chain.from_iterable(self.processes):
            p.start()
        start_queue = self.queues[0]
        for i, item in enumerate(self.collection):
            start_queue.put(MultiProcessPipeline.Task(self.start_func, item, index=i))
        for _ in range(self.start_size):
            start_queue.put(None)

    def join(self, ignore_results):
        # Skip joining the last queue - no one is taking from it
        for q in self.queues[:1]:
            q.join()

        last_q = self.queues[-1]
        stops, results = 0, []
        while stops < self.end_size:
            result_task = last_q.get()
            if result_task is None:
                stops += 1
            elif not ignore_results:
                results.append(result_task)
        return (t.result for t in sorted(results, key=lambda t: t.index))

    @staticmethod
    def get_num_stops(x, y):
        integer, reminder = (1, 0) if y is None else (int(y / x), y % x)
        for i in range(x):
            yield integer + (0 if i else reminder)

    class Task:
        def __init__(self, func, arg, index):
            self.func = func
            self.arg = arg
            self.result = arg
            self.index = index

        def __call__(self):
            if self.func:
                self.result = self.func(self.arg)
            return self

        def __str__(self):
            return f"[{self.index}] {self.result}"

    class Consumer(multiprocessing.Process):
        def __init__(self, readq, writeq, barrier, num_pills, next_func):
            super().__init__()
            self.readq = readq
            self.writeq = writeq
            self.num_pills = num_pills
            self.barrier = barrier
            self.next_func = next_func

        def run(self):
            # proc_name = self.name
            # Poison pill means shutdown
            for next_task in iter(self.readq.get, None):
                task = next_task()
                self.readq.task_done()
                self.writeq.put(MultiProcessPipeline.Task(self.next_func, task.result, task.index))

            self.readq.task_done()
            self.barrier.wait()
            for _ in range(self.num_pills):
                self.writeq.put(None)


class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)


class CustomMultiProcessPool(multiprocessing.pool.Pool):
    """
    sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
    because the latter is only a wrapper function, not a proper class.
    """

    Process = NoDaemonProcess


class _WorkersPool:
    """
    Wrapper to all kinds of parallel execution pools
     - Multiprocessing
     - ThreadPool (from multiprocessing package)
     - ThreadPoolExecutor
     - Gevents Pool
    """

    def __iter__(self):
        """Pool iterator"""
        for p in {
            pool
            for pool in {
                WorkersPool.multiprocess,
                WorkersPool.thread_pool,
                WorkersPool.thread_pool_executor,
                WorkersPool.greenlets,
            }
            if pool
        }:
            yield p

    @classmethod
    def pool_factory(cls, debug, pool_type, mgmt=False):
        """
        :param pool_type: Pool type to get
        :param debug: True run dummy pool
        :param mgmt: Get management pool
        :return: Callable, function
        """
        if debug:
            return cls.serial_pool
        if mgmt:
            return cls.management
        if pool_type is None:
            return cls.default
        pool_class = getattr(cls, pool_type, None)
        assert pool_class, f"Unknown pool_type: {pool_type} [{type(pool_type)}]." + "Supported: {}".format(
            "\n -".join(cls.choices())
        )
        return pool_class

    @classmethod
    def futures_process_pool(cls, key_to_func, workers):
        return cls.futures_pool(key_to_func, workers, engine=cls.process_pool_executor)

    @classmethod
    def futures_thread_pool(cls, key_to_func, workers):
        return cls.futures_pool(key_to_func, workers, engine=cls.thread_pool_executor)

    @classmethod
    def futures_pool(cls, key_to_func, workers, engine):
        assert isinstance(key_to_func, dict)
        with engine(workers) as pool:
            future_to_key = {pool.submit(func): key for key, func in key_to_func.items()}
            for future in concurrent.futures.as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    data = future.result()
                    yield key, data
                except (Exception,):
                    logger.exception(f"Generated an exception: {key}")

    @classmethod
    def get_default_pool_class(cls):
        return cls.multiprocess

    @classmethod
    @lru_cache(1)
    def choices(cls):
        return ["multiprocess", "thread_pool", "thread_pool_executor", "greenlets"]

    @classmethod
    def serial_pool(cls, *args, **kwargs):
        return WorkersPool.SerialPool()

    @classmethod
    def management(cls, workers=None):
        return cls.thread_pool(workers)

    @classmethod
    def default(cls, workers=None):
        return cls.get_default_pool_class()(workers)

    @classmethod
    def thread_pool(cls, workers=None):
        assert ThreadPool, "Please install multiprocessing package"
        return WorkersPool.Executor(ThreadPool, workers)

    @classmethod
    def process_pool_executor(cls, workers=None):
        assert ProcessPoolExecutor, "Please install ProcessPoolExecutor"
        return WorkersPool.Executor(ProcessPoolExecutor, workers)

    @classmethod
    def thread_pool_executor(cls, workers=None):
        assert ThreadPoolExecutor, "Please install ThreadPoolExecutor"
        return WorkersPool.Executor(ThreadPoolExecutor, workers)

    @classmethod
    def multiprocess(cls, workers=None):
        assert Pool, "Please install multiprocessing"
        return WorkersPool.Executor(CustomMultiProcessPool, workers or cpu_count())

    @classmethod
    def greenlets(cls, workers=None):
        assert GreenThreadPool, "Please install gevent package (ThreadPoolExecutor)"
        return WorkersPool.Executor(GreenThreadPool, workers)

    class SerialPool:
        """
        Acts like a pool but runs serially
        """

        def __init__(self):
            self.workers = 1

        def __str__(self):
            return "DummyPool"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # propagate exception
            pass

        def map_async(self, func, collection):
            return self.map(func, collection)

        @staticmethod
        def map(func, collection):
            return [func(f) for f in collection]

    class Executor:
        def __init__(self, threadpool, workers):
            self.workers = workers or DEFAULT_WORKERS
            self._pool = threadpool(self.workers)

        def __str__(self):
            return str(self._pool)

        def __enter__(self):
            return self._pool.__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._pool.__exit__(exc_type, exc_val, exc_tb)


WorkersPool = _WorkersPool()
