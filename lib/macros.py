# macros.py — Macro storage and loading

import json
import os

_MACRO_DIR = '/macros'

def _ensure_dir():
    try:
        os.mkdir(_MACRO_DIR)
    except OSError:
        pass

def save(name, macro):
    _ensure_dir()
    path = '{}/{}.json'.format(_MACRO_DIR, name)
    with open(path, 'w') as f:
        json.dump(macro, f)

def load(name):
    path = '{}/{}.json'.format(_MACRO_DIR, name)
    with open(path, 'r') as f:
        return json.load(f)

def list_macros():
    _ensure_dir()
    files = os.listdir(_MACRO_DIR)
    return [f[:-5] for f in files if f.endswith('.json')]

def delete(name):
    path = '{}/{}.json'.format(_MACRO_DIR, name)
    os.remove(path)