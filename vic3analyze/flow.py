import pyautogui
import time
from subprocess import Popen
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


def wait_until_found(wait_image, timeout=60):
    t = 0
    while True:
        print(f"Waiting to see {wait_image}")
        res = pyautogui.locateOnScreen(f"vic3analyze/captures/{wait_image}.png", confidence=0.9,
                                             grayscale=True)
        if res is None:
            if timeout != 0:
                t = t + 1
                if t > timeout:
                    raise Exception("Timed out waiting on image")



def try_click_or_abort(button_image, retry=10, rt_delay=0.5, esc_on_retry=False):
    while True:
        print(f"Looking for button {button_image}")
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
    Popen([game_bin, '-debug_mode'])
    time.sleep(20)  # TODO : find a better way to wait for game launch
    return
    # Popen([launcher_bin])
    # time.sleep(10)
    # try_click_or_abort('launcher_ignoresteam')
    # try_click_or_abort('launcher_play')
    # time.sleep(20)


def begin_newgame():
    log.info("Beginning new game")
    try_click_or_abort('mainmenu_newgame')
    time.sleep(0.5)
    try_click_or_abort('newgame_sandbox')
    time.sleep(7)  # TODO : detect the loading here better
    try_click_or_abort('newgame_observe')
    time.sleep(0.5)
    

def run_game():
    begin_newgame()
    log.info("Setting speed to 5")
    pyautogui.press('5')
    time.sleep(4)  # Takes a few secs for the animation to geti nto gameplay
                   # TODO : detect gameplay better
    log.info("Unpausing")
    pyautogui.press('space')


def grab_replay(callback, file):
    # Copy file to tmp dir
    rnd_asc = ''.join(random.choice(string.ascii_letters) for _ in range(6))
    save_fname = 'analyze_{}.v3'.format(rnd_asc)
    new_name = os.path.join(pdx_saves_dir, save_fname)
    shutil.copyfile(file, new_name)
    log.info("Capturing save file {new_name}")

    # TODO: instantiate new process here and also make sureo ld files
    #       are deleted
    callback(new_name)


def run_single(callback):
    startup_game()
    run_game()

    last_time = time.time()
    while True:
        time.sleep(0.5)
        try:
            save_f = os.path.join(pdx_saves_dir, 'autosave.v3')
            # TODO: handle if no autosave file is present
            ctime = os.stat(save_f).st_ctime
            if ctime > last_time:
                    grab_replay(callback, save_f)
                    last_time = ctime
        except FileNotFoundError:
            log.warning("Failed to capture file, maybe it's being written still?")
            continue
