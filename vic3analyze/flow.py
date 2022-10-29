import pyautogui
import time
from datetime import datetime
import subprocess
import tempfile
import os
import shutil
import string
import random
import logging
import re

log = logging.getLogger()

paused = False
abort = False


# def toggle_pause():
#     global paused
#     paused = not paused
#     print("Pause signal recieved, pause={}")
# def set_abort():
#     global abort
#     print("Abort signal recieved; exiting")
#     abort = True
#
# keyboard.on_press('f11', toggle_pause)
# keyboard.on_press('f9', set_abort)
time.sleep(3)

savedir = tempfile.mkdtemp()
pdx_saves_dir = os.path.expanduser('~/.local/share/Paradox Interactive/Victoria 3/save games/')
launcher_bin = os.path.expanduser('~/.steam/steam/steamapps/common/Victoria 3/launcher/dowser')
game_bin = os.path.expanduser('~/.steam/steam/steamapps/common/Victoria 3/binaries/victoria3')

process_re = re.compile(r'^Processing tick: ([0-9.]+)$')


def wait_until_found(wait_image, timeout=60):
    t = 0
    print(f"Waiting to see {wait_image}")
    while True:
        res = pyautogui.locateOnScreen(f"vic3analyze/captures/{wait_image}.png", confidence=0.9,
                                             grayscale=True)
        if res is None:
            if timeout != 0:
                t = t + 1
                if t > timeout:
                    raise Exception("Timed out waiting on image")



def try_click_or_abort(button_image, retry=10, rt_delay=0.5, esc_on_retry=False):
    print(f"Looking for button {button_image}")
    while True:
        try:
            res = pyautogui.locateCenterOnScreen(f"vic3analyze/captures/{button_image}.png", confidence=0.9,
                                                 grayscale=True)
            if res is None:
                retry = retry - 1
                time.sleep(rt_delay)
                if esc_on_retry:
                    pyautogui.press('esc')
                if retry <= 0:
                    raise Exception("Failed to get that button")
                continue
            bx, by = res
            pyautogui.moveTo(bx, by, 0.5, pyautogui.easeInOutQuad)
            pyautogui.mouseDown()
            time.sleep(0.1)
            pyautogui.mouseUp()
            return
        except pyautogui.ImageNotFoundException:
            retry = retry - 1
            if retry <= 0:
                raise
            if esc_on_retry:
                pyautogui.press('esc')
            time.sleep(rt_delay)
            continue


def startup_game():
    log.info("Starting game client")
    p = subprocess.Popen([game_bin, '-debug_mode'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(10)  # TODO : find a better way to wait for game launch
    return p
    # Popen([launcher_bin])
    # time.sleep(10)
    # try_click_or_abort('launcher_ignoresteam')
    # try_click_or_abort('launcher_play')
    # time.sleep(20)


def begin_newgame():
    log.info("Beginning new game")
    try_click_or_abort('mainmenu_newgame', retry=40)
    try_click_or_abort('newgame_sandbox')
    try_click_or_abort('newgame_observe', retry=80)
    

def run_game():
    begin_newgame()
    log.info("Setting speed to 5")
    pyautogui.press('5')
    time.sleep(4)  # Takes a few secs for the animation to geti nto gameplay
                   # TODO : detect gameplay better
    log.info("Unpausing")
    pyautogui.press('space')


def end_game():
    log.info("returning to main menu")
    pyautogui.press('esc')
    try_click_or_abort('pause_exit')
    try_click_or_abort('pause_confirm_exitmainmenu')


def shutdown_game():
    try_click_or_abort('mainmenu_exit')


def grab_replay(callback, file):
    # Copy file to tmp dir
    rnd_asc = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    save_fname = 'analyze_{}.v3'.format(rnd_asc)
    new_name = os.path.join(pdx_saves_dir, save_fname)
    shutil.copyfile(file, new_name)

    with open(new_name) as f:
        m = re.search(r'date=([0-9\.]+)', f.read())
        intdata = [int(d) for d in m.group(1).split(".")]
        date = datetime(*intdata)

    # TODO: instantiate new process here and also make sureo ld files
    #       are deleted
    log.info(f"Capturing save file {new_name} for {date}")
    callback(new_name)
    return date


def capture_single_run(callback, until=None):
    run_game()

    try:
        done = False
        last_time = time.time()
        while not done:
            time.sleep(0.5)
            try:
                save_f = os.path.join(pdx_saves_dir, 'autosave.v3')
                # TODO: handle if no autosave file is present
                ctime = os.stat(save_f).st_ctime
                if ctime > last_time:
                    date = grab_replay(callback, save_f)
                    last_time = ctime
                    if date > until:
                        log.info("Finished captures for this run")
                        done=True
            except FileNotFoundError:
                log.warning("Failed to capture file, maybe it's being written still?")
                continue
    finally:
        log.error("Exception in capturing run!")
        end_game()


def run(callback, num_runs=1, until=None):
    startup_game()
    try:
        if num_runs == 0:
            while True:
                capture_single_run(callback, until)
        else:
            for _ in range(num_runs):
                capture_single_run(callback, until)
                time.sleep(10)
    finally:
        log.error("Exception in running flow!")
        shutdown_game()
