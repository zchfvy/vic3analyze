import os
from appdirs import user_data_dir

_config = {}

from sys import platform
if platform == "linux" or platform == "linux2":
    # linux
    game_dir = os.path.expanduser('~/.steam/steam/steamapps/common/Victoria 3')
elif platform == "darwin":
    # OS X
    # Just assumin it's the same as linux, don't know for sure
    game_dir = os.path.expanduser('~/.steam/steam/steamapps/common/Victoria 3')
elif platform == "win32":
    # Windows...
    game_dir = r'C:\Program Files\Steam\steamapps\common\Victoria 3'

saves_dir = os.path.join(user_data_dir('Paradox Interactive', 'Victoria 3'), 'save games')

_config['game_dir'] = game_dir
_config['saves_dir'] = saves_dir


def get_config(key):
    return _config[key]


def set_config(key, val):
    config[key] = val
