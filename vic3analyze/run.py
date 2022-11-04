import os
from multiprocessing import Process
import logging
import argparse

from dateutil import parser as dateparser
import coloredlogs

import process_savegame
import flow
import conf

# logging.basicConfig(level=logging.INFO)
coloredlogs.install(level='INFO')

log = logging.getLogger(__name__)

def replay_proc(filename):
    logging.basicConfig(level=logging.DEBUG)
    log.info("Process thread running")
    try:
        process_savegame.process(filename)
    finally:
        os.remove(filename)  # TODO : this is a bit bodgey and manual

def replay_callback(filename):
    log.info("Starting process thread")
    p = Process(target=replay_proc, args=(filename,))
    p.start()

parser = argparse.ArgumentParser()
parser.add_argument('--until', default='1935-12-31')
parser.add_argument('--runs', default=1, type=int)

parser.add_argument('--vic3')
parser.add_argument('--save-dir')

args = parser.parse_args()

until = dateparser.parse(args.until)
if args.vic3 is not None:
    log.info(f"Setting vic3 location to '{args.vic3}'")
    conf.set_config('game_dir', args.vic3)
if args.save_dir is not None:
    log.info(f"Setting saves location to '{args.save_dir}'")
    conf.set_config('game_dir', args.save_dir)

flow.run(replay_callback, num_runs=args.runs, until=until)
