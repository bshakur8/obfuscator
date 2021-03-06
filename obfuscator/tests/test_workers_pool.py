import unittest

from strategy.workers_pool import WorkersPool
from strategy import utils

utils.init_logger()


def multiply(x):
    return x ** 5


def run_me(pool, list_num):
    return list(pool.map(multiply, list_num))


class TestWorkersPool(unittest.TestCase):

    def test_choices(self):
        choices = WorkersPool.choices()
        self.assertEqual(len(choices), 11)
        self.assertTrue(type(WorkersPool.default(5)),
                        type(WorkersPool.thread_pool(5)))

    def _test_pool_result(self):
        workers = 3
        expected_result = [32, 243, 1024, 3125]
        with WorkersPool.multiprocess(workers) as pool1, \
                WorkersPool.thread_pool_executor(workers) as pool2, \
                WorkersPool.thread_pool(workers) as pool3, \
                WorkersPool.greenlets(workers) as pool4:

            for index, pool in enumerate((pool1, pool2, pool3, pool4), 1):
                utils.logger.info(f"Pool #{index}")
                self.assertEqual(run_me(pool1, range(2, 6)), expected_result)
