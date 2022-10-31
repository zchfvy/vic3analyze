import flow
import os
import process_savegame
from multiprocessing import Process

import logging
import argparse
from dateutil import parser as dateparser

import coloredlogs

# logging.basicConfig(level=logging.INFO)
coloredlogs.install(level='INFO')

def replay_proc(filename):
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Process thread running")
    try:
        process_savegame.process(filename)
    finally:
        os.remove(filename)  # TODO : this is a bit bodgey and manual

def replay_callback(filename):
    logging.info("Starting process thread")
    p = Process(target=replay_proc, args=(filename,))
    p.start()

parser = argparse.ArgumentParser()
parser.add_argument('--until', default='1935-12-31')
parser.add_argument('--runs', default=1, type=int)

args = parser.parse_args()

until = dateparser.parse(args.until)

flow.run(replay_callback, num_runs=args.runs, until=until)
