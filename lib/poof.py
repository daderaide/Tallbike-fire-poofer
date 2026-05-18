# poof.py — Safety manager and relay control (relay box only)

import time
import json
from hardware import i2c, igniter
from comms import modbus

# PCF8574A address
RELAY_ADDR = 0x21

# All relays off (active low, so 0xFF = all off)
ALL_OFF = 0xFF

# State
armed = False
relay_bitmask = ALL_OFF
last_comms_time = time.ticks_ms()
COMMS_TIMEOUT_MS = 500

# Executor (lazy init)
_executor = None

# Macro storage
_macros = {}

def _resolve_macro(idx):
    """Resolve macro index to macro dict. 0=main_poof, 1+=aux by sorted name."""
    if idx == 0:
        return _macros.get('main_poof')
    macro_names = sorted([k for k in _macros.keys() if k != 'main_poof'])
    i = idx - 1
    if 0 <= i < len(macro_names):
        return _macros[macro_names[i]]
    return None

def update_comms_time():
    global last_comms_time
    last_comms_time = time.ticks_ms()

def check_watchdog():
    if time.ticks_diff(time.ticks_ms(), last_comms_time) > COMMS_TIMEOUT_MS:
        emergency_stop()
        modbus.set_hreg(0, 3)
        modbus.set_hreg(8, 1)

def set_relays(bitmask):
    global relay_bitmask
    relay_bitmask = bitmask
    i2c.writeto(RELAY_ADDR, bytes([relay_bitmask]))
    modbus.set_hreg(1, relay_bitmask)

def set_igniter(state):
    igniter.value(state)
    modbus.set_hreg(3, state)

def emergency_stop():
    global armed, _executor
    armed = False
    set_relays(ALL_OFF)
    set_igniter(0)
    if _executor is not None:
        _executor.state = 0
        _executor._ign_active = False
        _executor.macro = None
    modbus.set_hreg(0, 0)
    modbus.set_hreg(9, 0)

def load_macros():
    global _macros
    import os
    _macros = {}
    try:
        files = os.listdir('/macros')
        for f in files:
            if f.endswith('.json'):
                name = f[:-5]
                try:
                    with open('/macros/' + f, 'r') as fp:
                        _macros[name] = json.load(fp)
                except:
                    pass
    except:
        pass

def get_macro(name):
    return _macros.get(name)

def process_commands():
    global armed, _executor

    if _executor is None:
        from executor import Executor
        _executor = Executor(set_relays, set_igniter)
        load_macros()

    changed = modbus.changed_hregs

    # Arm/disarm
    if 100 in changed:
        val = modbus.get_hreg(100)
        if val == 1:
            armed = True
            modbus.set_hreg(0, 1)
            modbus.set_hreg(8, 0)
        else:
            armed = False
            emergency_stop()
        modbus._remove_changed_register('HREGS', 100, changed[100]['time'])

    # Combined macro select + fire (register 102)
    # value 0-N = press with macro index, 0xFFFF = release
    RELEASE = 0xFFFF
    if 102 in changed:
        val = modbus.get_hreg(102)
        btn_pressed = val != RELEASE
        # print('POOF: reg102={} pressed={} armed={} running={}'.format(val, btn_pressed, armed, _executor.running))

        _executor.set_button_state(btn_pressed)

        if btn_pressed and armed and not _executor.running:
            macro = _resolve_macro(val)
            # print('POOF: resolved macro={}'.format('OK' if macro else 'NONE'))
            if macro:
                # print('POOF: starting macro, steps={}'.format(len(macro.get('steps', []))))
                _executor.start(macro)
        elif not btn_pressed and not _executor.running:
            set_relays(ALL_OFF)
            set_igniter(0)
            if armed:
                modbus.set_hreg(0, 1)
        # elif not btn_pressed and _executor.running:
        #     print('POOF: release while running, state={}'.format(_executor.state))

        modbus._remove_changed_register('HREGS', 102, changed[102]['time'])

    # Config sync (receive macro data from control box)
    if 200 in changed or 232 in changed:
        _handle_config_sync(changed)

    # Update executor
    if _executor.running:
        _executor.update()

# Config sync buffer
_config_buf = bytearray()
_config_expected_len = 0

def _handle_config_sync(changed):
    global _config_buf, _config_expected_len

    # Buffer chunk data when a new chunk arrives (register 200 changed)
    if 200 in changed:
        length = modbus.get_hreg(200)
        offset = modbus.get_hreg(201)

        if offset == 0:
            _config_expected_len = length
            _config_buf = bytearray(length)

        # Read 30 data registers (60 bytes per chunk)
        chunk = bytearray()
        for reg in range(202, 232):
            val = modbus.get_hreg(reg)
            chunk.append((val >> 8) & 0xFF)
            chunk.append(val & 0xFF)

        end = min(offset + len(chunk), _config_expected_len)
        _config_buf[offset:end] = chunk[:end - offset]

    # Check if complete (checksum register written)
    if 232 in changed:
        checksum = modbus.get_hreg(232)
        calc_sum = sum(_config_buf) & 0xFFFF
        if calc_sum == checksum:
            try:
                config_str = _config_buf.decode('utf-8').rstrip('\x00')
                config = json.loads(config_str)
                if 'macros' in config:
                    import os
                    try:
                        os.mkdir('/macros')
                    except:
                        pass
                    # Write incoming macros
                    incoming = set()
                    for name, macro in config['macros'].items():
                        incoming.add(name)
                        with open('/macros/{}.json'.format(name), 'w') as f:
                            json.dump(macro, f)
                    # Delete macros not in payload (except main_poof)
                    for f in os.listdir('/macros'):
                        if f.endswith('.json'):
                            fname = f[:-5]
                            if fname not in incoming:
                                os.remove('/macros/' + f)
                    load_macros()
                modbus.set_hreg(103, 0)
            except:
                modbus.set_hreg(8, 5)

    for reg in range(200, 233):
        if reg in changed:
            modbus._remove_changed_register('HREGS', reg, changed[reg]['time'])