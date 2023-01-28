import os
import platform
from datetime import datetime
from collections import namedtuple
import logging
import re
import signal

import lark

log = logging.getLogger(__name__)

Color = namedtuple('Color', ['r', 'g', 'b'])
Keyval = namedtuple('Keyval', ['k', 'v'])


my_dir = os.path.dirname(os.path.realpath(__file__))
lalr = lark.Lark(open(os.path.join(my_dir, 'pdx_data.lark')).read(), parser='lalr')

@profile
def parse(filename):
    pyver = platform.python_implementation()
    if pyver == 'CPython':
        # Try to dfind and relaunch as pypy
        expected_pypy_dir = os.path.join(my_dir, '..', '.pypy')
        if os.path.exists(expected_pypy_dir):
            log.info("""PyPy detected, attempting parsing using it""")
            import tempfile
            import dill
            from subprocess import Popen
            with tempfile.TemporaryDirectory() as tmpdir:
                # To do this we must do a bit of black magic
                out_file = os.path.join(tmpdir, 'replay.dill')
                scrip = """
                """
                p = Popen([
                    os.path.join(expected_pypy_dir, 'bin', 'python'),
                    __file__, filename, out_file
                    ])
                res = p.wait()
                if res != 0:
                    if res < 0:
                        sig = signal.Signals(-res)
                        log.error(f"Pypy process terminated by signal {-res} ({sig})")
                        raise Exception(f"Script terminated")
                    else:
                        raise Exception(f"Error in PyPy: Return code {res}!")
                log.info("""Reading back data from PyPy""")
                with open(out_file, 'rb') as f:
                    return dill.load(f)
        else:
            log.warn("""
                Running parser on CPython is very slow, it is reccomended to use PyPy
                """)



    log.info(f"Reading savefile")
    with open(filename, 'r') as savefile:
        rawdata = savefile.read()

    # HACK, some files start with wierd high-unicode bytes that break the
    # parser
    if ord(rawdata[0]) > 127:
        rawdata = rawdata[1:]
    # Strip header for replays only
    rawdata = re.sub('^SAV[0-9a-f]{20}', '', rawdata)
    # Remove comments
    rawdata = re.sub('#.*', '', rawdata).strip()


    log.info(f"Parsing save data into AST")
    try:
        ast = lalr.parse(rawdata)
    except:
        print("Error in parsing pre-processed data. Data in parse.out")
        with open('parse.out', 'w') as f:
            f.write(rawdata)
        raise
    log.info(f"Parsing AST into data structure")
    return parse_tree(ast)


def parse_token(token):
    if token.type == "QUOT_STR":
        return str(token.value[1:-1])
    if token.type == "RAW_STR":
        return str(token.value)
    if token.type == "DATE":
        data = token.value.split(".")
        intdata = [int(d) for d in data]
        return datetime(*intdata)
    if token.type == "NUMBER":
        return float(token.value)
    if token.type == "INTEGER":
        return int(token.value)


def parse_tree(node):
    if isinstance(node, lark.Token):
        return parse_token(node)

    if node.data == 'start':
        return parse_tree(node.children[0])
    elif node.data == 'keyvalue':
        key = parse_tree(node.children[0])
        val = parse_tree(node.children[1])
        return Keyval(key, val)
    elif node.data == 'list':
        res = []
        for ch in node.children:
            res.append(parse_tree(ch))
        # There are multiple possible list types
        #  Plain lists (all not keyval)
        #  Simple dicsts (all keyval wiht uniqe key)
        #  Complex dicsts (all keyval, some multiple keys)
        #  Wierd hybrids (soem of both)
        if all(isinstance(r, Keyval) for r in res):
            dict_res = {}
            for kv in res:
                if kv.k in dict_res:
                    if not isinstance(dict_res[kv.k], list):
                        old_val = dict_res[kv.k]
                        dict_res[kv.k] = [old_val]
                    dict_res[kv.k].append(kv.v)
                else:
                    dict_res[kv.k] = kv.v
            res = dict_res
        return res
    elif node.data == 'color':
        red = parse_tree(node.children[1])
        grn = parse_tree(node.children[2])
        blu = parse_tree(node.children[3])
        return Color(red, grn, blu)


if __name__ == '__main__':
    import sys
    import dill
    import coloredlogs

    coloredlogs.install(level='DEBUG')

    f_in = sys.argv[1]
    f_out = sys.argv[2]

    log.info("Reading data from replay file")
    result = parse(f_in)

    with open(f_out, 'wb') as f:
        log.info("Dumping data to dill")
        dill.dump(result, f)
    log.info("Completed succesfully")
    exit(0)
