#!/usr/bin/env python3
from functools import lru_cache

try:
    from concurrent.futures.thread import ThreadPoolExecutor
except ImportError:
    ThreadPoolExecutor = None
try:
    from multiprocessing import Pool, cpu_count, Manager

    # Shared lookup table between all processes
    LOOKUP_TABLE = Manager().dict()
except ImportError:
    Pool = None
    cpu_count = lambda: 1
    Manager = None
    LOOKUP_TABLE = None
try:
    from multiprocessing.pool import ThreadPool
except ImportError:
    ThreadPool = None
try:
    from gevent.threadpool import ThreadPoolExecutor as GreenThreadPool
except ImportError:
    GreenThreadPool = None

DEFAULT_WORKERS = 3


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
        for pool in (pool for pool in (WorkersPool.multiprocess,
                                       WorkersPool.thread_pool,
                                       WorkersPool.thread_pool_executor,
                                       WorkersPool.greenlets)
                     if pool):
            yield pool

    @classmethod
    def pool_factory(cls, pool_type):
        """
        :param pool_type: Pool type to get
        :return: Callable, function
        """
        if pool_type is None:
            return cls.default
        pool_class = getattr(cls, pool_type, None)
        assert pool_class, "Unknown pool_type: {pool_type} [{type(pool_type)}]." + \
                           "Supported: {}".format('\n -'.join(cls.choices()))
        return pool_class

    @classmethod
    def get_default_pool_class(cls):
        return cls.multiprocess

    @classmethod
    @lru_cache(1)
    def choices(cls):
        return [fn for fn in cls.__dict__ if not fn.startswith("_")
                and fn not in ('pool_factory', 'choices', 'choices_str', 'default', 'Executor',
                               'get_default_pool_class')]

    @classmethod
    def default(cls, workers=None):
        return cls.get_default_pool_class()(workers)

    @classmethod
    def thread_pool(cls, workers=None):
        assert ThreadPool, "Please install multiprocessing package"
        return WorkersPool.Executor(ThreadPool, workers)

    @classmethod
    def thread_pool_executor(cls, workers=None):
        assert ThreadPoolExecutor, "Please install ThreadPoolExecutor"
        return WorkersPool.Executor(ThreadPoolExecutor, workers)

    @classmethod
    def multiprocess(cls, workers=None):
        assert Pool, "Please install multiprocessing"
        return WorkersPool.Executor(Pool, workers or cpu_count())

    @classmethod
    def greenlets(cls, workers=None):
        assert GreenThreadPool, "Please install gevent package (ThreadPoolExecutor)"
        return WorkersPool.Executor(GreenThreadPool, workers)

    class Executor:
        def __init__(self, threadpool, workers, lookup_table=None):
            self.workers = workers or DEFAULT_WORKERS
            self._pool = threadpool(self.workers)
            # Use external lookup table
            self.lookup_table = lookup_table

        def __str__(self):
            return str(self._pool)

        def __enter__(self):
            return self._pool.__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._pool.__exit__(exc_type, exc_val, exc_tb)


WorkersPool = _WorkersPool()
