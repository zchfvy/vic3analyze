import flow
import os
import process_savegame
from multiprocessing import Process

import logging
import argparse
from dateutil import parser as dateparser

logging.basicConfig(level=logging.INFO)

def replay_proc(filename):
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Process thread running")
    process_savegame.process(filename)
    os.remove(filename)  # TODO : this is a bit bodgey and manual

def replay_callback(filename):
    logging.info("Starting process thread")
    p = Process(target=replay_proc, args=(filename,))
    p.start()

parser = argparse.ArgumentParser()
parser.add_argument('--until', default='1935-12-31')

args = parser.parse_args()

until = dateparser.parse(args.until)

flow.run_single(replay_callback, until)
