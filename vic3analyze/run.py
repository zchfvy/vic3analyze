import os
from multiprocessing import Process, Queue
import logging
import argparse

from dateutil import parser as dateparser
import coloredlogs

import process_savegame
import flow
import conf
import tempfile
from tqdm import tqdm

# logging.basicConfig(level=logging.INFO)
coloredlogs.install(level='INFO')

log = logging.getLogger(__name__)

def worker(queue, collect_only):
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("worker")
    log.info("Process thread running")
    for replayfile, run_internal_id in iter(queue.get, 'STOP'):
        log.info(f"Got replay item ({queue.qsize()} in queue)")
        try:
            if collect_only:
                import zipfile
                output_dir = './output'  # TODO : determine output dir better
                zf_name = os.path.join(output_dir, f"run_{run_internal_id}.zip")
                rf_name = os.path.basename(replayfile)
                with zipfile.ZipFile(zf_name, 'a', compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(replayfile, arcname=rf_name)
            else:
                process_savegame.process(replayfile)
        except process_savegame.DuplicateSampleError:
            continue
        except:
            log.exception("Uncaught exception in worker")
            queue.put((replayfile, run_internal_id))
        finally:
            if os.path.exists(replayfile):
                os.remove(replayfile)  # TODO : this is a bit bodgey and manual

parser = argparse.ArgumentParser()
parser.add_argument('--until', default='1935-12-31')
parser.add_argument('--runs', default=1, type=int)

parser.add_argument('--vic3')
parser.add_argument('--save-dir')

parser.add_argument('--num-workers', default=6, type=int)
parser.add_argument('--collect-only', action='store_true')
parser.add_argument('--process-offline-zip', default=None)

args = parser.parse_args()

if args.process_offline_zip and args.collect_only:
    log.error("""\
    --collect-only and --process-ofline-zip cannot be used at the same time""")
    exit(1)

until = dateparser.parse(args.until)
if args.vic3 is not None:
    log.info(f"Setting vic3 location to '{args.vic3}'")
    conf.set_config('game_dir', args.vic3)
if args.save_dir is not None:
    log.info(f"Setting saves location to '{args.save_dir}'")
    conf.set_config('game_dir', args.save_dir)

task_queue = Queue()
try:
    for i in range(args.num_workers):
        Process(target=worker, args=(task_queue, args.collect_only)).start()

    def replay_callback(filename, run_id):
        log.info("Enquing work item")
        task_queue.put((filename, run_id))

    if args.process_offline_zip is not None:
        import zipfile
        import tempfile
        import time
        with zipfile.ZipFile(args.process_offline_zip, 'r') as zf:
            members = zf.namelist()
            last_sub = time.time()
            with tempfile.TemporaryDirectory() as tmpdir:
                for m in tqdm(members):
                    if time.time() - last_sub < 1:
                        time.sleep(2)  # smear times of processes
                    zf.extract(m, tmpdir)
                    fname = os.path.join(tmpdir, m)
                    replay_callback(fname, args.process_offline_zip)
                    last_sub = time.time()
                    while task_queue.qsize() > args.num_workers:
                        time.sleep(1)

    else:
        flow.run(replay_callback, num_runs=args.runs, until=until)
except:
    log.exception("Analyzer exiting with uncaught exception")
finally:
    for i in range(args.num_workers):
        task_queue.put('STOP')
