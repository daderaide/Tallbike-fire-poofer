# safety.py — Safety manager and relay control (relay box only)

import time
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

def update_comms_time():
    global last_comms_time
    last_comms_time = time.ticks_ms()

def check_watchdog():
    if time.ticks_diff(time.ticks_ms(), last_comms_time) > COMMS_TIMEOUT_MS:
        emergency_stop()
        modbus.set_hreg(0, 3)   # system_state = error
        modbus.set_hreg(8, 1)   # error_code = comms_timeout

def set_relays(bitmask):
    global relay_bitmask
    relay_bitmask = bitmask
    i2c.writeto(RELAY_ADDR, bytes([relay_bitmask]))
    modbus.set_hreg(1, relay_bitmask)

def set_igniter(state):
    igniter.value(state)
    modbus.set_hreg(3, state)

def emergency_stop():
    global armed
    armed = False
    set_relays(ALL_OFF)
    set_igniter(0)
    modbus.set_hreg(0, 0)   # system_state = idle
    modbus.set_hreg(9, 0)   # active_macro = none

def process_commands():
    global armed

    changed = modbus.changed_hregs

    if 100 in changed:
        val = modbus.get_hreg(100)
        if val == 1:
            armed = True
            modbus.set_hreg(0, 1)   # system_state = armed
            modbus.set_hreg(8, 0)   # clear error
        else:
            armed = False
            emergency_stop()
        modbus._remove_changed_register('HREGS', 100, changed[100]['time'])

    if 101 in changed:
        val = modbus.get_hreg(101)
        if val == 1 and armed:
            set_igniter(1)
            set_relays(0x00)        # all 8 relays on (active low)
            modbus.set_hreg(0, 2)   # system_state = firing
        elif val == 0:
            set_relays(ALL_OFF)
            set_igniter(0)
            if armed:
                modbus.set_hreg(0, 1)   # back to armed
        modbus._remove_changed_register('HREGS', 101, changed[101]['time'])