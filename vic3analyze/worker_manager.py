import signal
from multiprocessing import Process, Queue
import logging
import time
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm


log = logging.getLogger(__name__)

STOP = 'STOP'


def _worker(worker_func, task_queue, worker_args):
    try:
        for item in iter(task_queue.get, STOP):
            try:
                worker_func(item, *worker_args)
            except KeyboardInterrupt:
                raise
            except:
                log.exception("Uncaught exception in worker")
                time.sleep(1)  # Back off a bit to controll error rate
                task_queue.put(item)
    except KeyboardInterrupt:
        log.warning("Aborting worker process thread")
    log.info("Worker thread completed all tasks")
    task_queue.put(STOP)


def run(jobs_list, enque_func, worker_func, num_workers=None, worker_args=[],
        enqueue_args=[]):
    task_queue = Queue()
    procs = []
    def _start_proc():
        p = Process(target=_worker, args=(worker_func, task_queue, worker_args))
        p.start()
        return p
    for i in range(num_workers):
        p = _start_proc()
        procs.append(p)

    if num_workers is None:
        num_workers = 6  # TODO -use system processor count
    max_queued_jobs = num_workers
    to_launch = num_workers

    try:
        for job in tqdm(jobs_list):

            try:
                queue_item = enque_func(job, *enqueue_args)
                if queue_item is not None:
                    task_queue.put(queue_item)
            except StopIteration:
                break

            while task_queue.qsize() >= max_queued_jobs:
                time.sleep(.1)
                for i in range(len(procs)):
                    if not procs[i].is_alive():
                        log.warning("Worker process seems to have failed, restarting")
                        procs[i] = _start_proc()
        log.info("All tasks scheduled, signalling end of computation")
        task_queue.put(STOP)
    except KeyboardInterrupt:
        log.error("Aborting main thread")
        task_queue.put(STOP)
    except:
        log.exception("Unknown error, aborting!")
        task_queue.put(STOP)
    finally:
        for p in procs:
            p.join()
