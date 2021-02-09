from threading import Thread, Lock, Event

from strategy import utils

STOP = object()


class ObfuscateWorker(Thread):
    def __init__(self, strategy, queue_class):
        super().__init__(name=f"worker:{strategy}")
        self.strategy = strategy
        self.queue = queue_class(-1)
        self.running = Event()
        self.running.set()
        self.lock = Lock()

    def put(self, abs_file):
        utils.logger.debug(f"worker {self.strategy} putting '{abs_file}' in queue")
        self.queue.put_nowait(abs_file)

    def join(self, timeout=None):
        # put something to let it continue
        utils.logger.info("Waiting for jobs to complete")
        self.queue.put_nowait(STOP)
        super().join(timeout)
        self.running.clear()

    def run(self):
        while self.running:
            try:
                abs_file = self.queue.get(block=True)
                if abs_file is STOP:
                    utils.logger.info(f"Stopping worker: {self.strategy}")
                    break
            except Exception as e:
                utils.logger.info('Exception ' + str(e))
            else:
                with self.lock:
                    utils.logger.info(f"worker {self.strategy} - {abs_file}")
                    # blocking
                    self.strategy.single_obfuscate(abs_file)
            self.queue.task_done()

        utils.logger.info(f"Worker: {self.strategy} stopped!")
