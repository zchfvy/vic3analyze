import flow
import process_savegame
from multiprocessing import Process

import logging

logging.basicConfig(level=logging.DEBUG)

def replay_proc(filename):
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Process thread running")
    process_savegame.process(filename)

def replay_callback(filename):
    logging.info("Starting process thread")
    p = Process(target=replay_proc, args=(filename,))
    p.start()


flow.run_single(replay_callback)
