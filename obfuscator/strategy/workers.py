import time
from queue import Empty
from threading import Thread, Event, BoundedSemaphore

from strategy import utils


class ObfuscateWorker(Thread):
    idx = 1

    def __init__(self, strategy, queue_class):
        super().__init__(name=f"worker: {strategy}", daemon=False)
        self.idx = ObfuscateWorker.idx
        self.idx += 1
        self.strategy = strategy
        self.running = Event()
        self.queue = queue_class(-1)
        self.running.set()
        self.semaphore = BoundedSemaphore(3)
        self.threads = set()

    def put(self, abs_file):
        utils.logger.debug(f"putting '{abs_file}' in {self.name} queue")
        self.queue.put_nowait(abs_file)

    def join(self, timeout=None):
        utils.logger.info(f"{self.name} Waiting for obfuscation jobs to complete")
        while not self.queue.empty() and self.semaphore._value > 0:
            time.sleep(0.5)
            utils.logger.info(f"{self.name} Waiting for obfuscation jobs to complete")

        [t.join() for t in self.threads if t.is_alive()]
        self.running.clear()
        super().join(timeout)

    def run(self):
        self.running.set()
        while self.running.is_set():
            self.threads = {t for t in self.threads if t.is_alive()}
            try:
                abs_file = self.queue.get(block=False)
            except Empty:
                time.sleep(0.1)
                continue
            except Exception as e:
                utils.logger.exception(f'exception: {str(e)}')
            else:
                with self.semaphore:
                    utils.logger.info(f"Obfuscating {abs_file}")
                    # blocking
                    # self.strategy.single_obfuscate(abs_file)

                    # non-blocking
                    name = f"{len(self.threads) + 1}"
                    t = Thread(target=self.strategy.single_obfuscate, args=(abs_file,), name=f"{self.idx}:{name}",
                               daemon=False)
                    t.start()
                    self.threads.add(t)
            self.queue.task_done()

        utils.logger.debug("stopped!")
