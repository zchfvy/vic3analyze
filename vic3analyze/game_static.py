import os

from parse import parse

game_root = os.path.expanduser('~/.steam/steam/steamapps/common/Victoria 3/game')

_configs_memo = {}

def get_config_file(config_name):
    if config_name not in _configs_memo:
        fname = os.path.join(game_root, config_name)
        contents = parse(fname)
        _configs_memo[config_name] = contents

    return _configs_memo[config_name]
