import os
import logging

from parse import parse
import conf

log = logging.getLogger(__name__)

_configs_memo = {}

def get_config_file(config_name):
    if config_name not in _configs_memo:
        log.info(f"Loading config file {config_name}")
        game_root = os.path.join(conf.get_config('game_dir'), 'game')
        fname = os.path.join(game_root, config_name)
        contents = parse(fname)
        _configs_memo[config_name] = contents

    return _configs_memo[config_name]
