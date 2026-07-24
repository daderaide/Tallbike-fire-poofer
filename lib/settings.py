# settings.py — Persistent settings (JSON on flash)

import json

_SETTINGS_FILE = '/settings.json'

_defaults = {
    'ring_pattern': 'blink_fade',
    'ring_brightness': 100,
    'aux_brightness': 100,
    'backlight': True,
}

_settings = {}

def load():
    global _settings
    try:
        with open(_SETTINGS_FILE, 'r') as f:
            _settings = json.load(f)
    except:
        _settings = {}
    # Fill in any missing keys with defaults
    for k, v in _defaults.items():
        if k not in _settings:
            _settings[k] = v

def save():
    with open(_SETTINGS_FILE, 'w') as f:
        json.dump(_settings, f)

def get(key):
    if not _settings:
        load()
    return _settings.get(key, _defaults.get(key))

def set(key, value):
    if not _settings:
        load()
    _settings[key] = value

def get_all():
    if not _settings:
        load()
    return _settings