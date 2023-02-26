import logging
import argparse
import time
import os

from dateutil import parser as dateparser
import coloredlogs

import process_savegame
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
            time.sleep(1)  # Back off a bit to controll error rate
            queue.put((replayfile, run_internal_id))
        else:
            if os.path.exists(replayfile):
                log.info(f"Removing file {replayfile}")
                os.remove(replayfile)  # TODO : this is a bit bodgey and manual

parser = argparse.ArgumentParser()
parser.add_argument('--until', default='1935-12-31')
parser.add_argument('--runs', default=1, type=int)

parser.add_argument('--vic3')
parser.add_argument('--save-dir')

parser.add_argument('--num-workers', default=6, type=int)
parser.add_argument('--collect-only', action='store_true')
parser.add_argument('--process-offline-zip', default=None)
parser.add_argument('--process-savegame', default=None)

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

try:

    if args.process_savegame is not None:
        process_savegame.process(args.process_savegame)

    elif args.process_offline_zip is not None:
        import zipfile
        import tempfile
        import worker_manager
        with zipfile.ZipFile(args.process_offline_zip, 'r') as zf:

            members = zf.namelist()
            with tempfile.TemporaryDirectory() as tmpdir:
                def en(m):
                    if process_savegame.check_exists(m):
                        log.info(f"Skipping exissting sample {m}")
                        return None
                    else:
                        log.info(f"New sample {m}")

                    log.info(f"Extracting {m} from archive")
                    try:
                        zf.extract(m, tmpdir)
                    except zipfile.BadZipFile:
                        log.error(f"Failed to extract file {m}")
                        return None
                    fname = os.path.join(tmpdir, m)
                    return(fname)

                def wk(replayfile):
                    if not os.path.exists(replayfile):
                        log.error(f"Replay file {replayfile} missing!")
                        return
                    try:
                        process_savegame.process(replayfile)
                    except process_savegame.DuplicateSampleError:
                        pass
                    if os.path.exists(replayfile):
                        log.info(f"Removing file {replayfile}")
                        os.remove(replayfile)  # TODO : this is a bit bodgey and manual

                worker_manager.run(zf.namelist(), en, wk,
                        num_workers=args.num_workers)

    else:
        from multiprocessing import Process, Queue
        import flow  # flow does some DISLAY stuff via pyautogui, so import it
                     # here

        def replay_callback(filename, run_id):
            log.info("Enquing work item")
            task_queue.put((filename, run_id))
            procs = []
        task_queue = Queue()
        for i in range(args.num_workers):
            p = Process(target=worker, args=(task_queue, args.collect_only)).start()
            procs.append(p)
        try:
            flow.run(replay_callback, num_runs=args.runs, until=until)
        finally:
            for i in range(args.num_workers):
                task_queue.put('STOP')
except:
    log.exception("Analyzer exiting with uncaught exception")
