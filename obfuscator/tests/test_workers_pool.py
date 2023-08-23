from ..lib.workers_pool import WorkersPool
from ..lib import utils

utils.init_logger()


def multiply(x):
    return x**5


def run_me(pool, list_num):
    return list(pool.map(multiply, list_num))


def test_choices():
    choices = WorkersPool.choices()
    assert len(choices) == 5
    default = WorkersPool.default()
    multiprocess = WorkersPool.multiprocess()
    assert isinstance(default, type(multiprocess))


def test_pool_result():
    for pool in WorkersPool.choices():
        with pool(workers=3) as curr_pool:
            assert run_me(curr_pool, range(2, 6)) == [32, 243, 1024, 3125]
