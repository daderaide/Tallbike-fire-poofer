# inputs.py — IRQ-driven input manager (control box only)
# Encoder rotation via quadrature decoding on CLK/DT
# Debounced click detection on encoder SW and aux button

from machine import Pin
import time

# --- Encoder rotation (IRQ on CLK) ---

_enc_clk = Pin(6, Pin.IN)
_enc_dt = Pin(5, Pin.IN)
_enc_delta = 0

def _enc_isr(pin):
    global _enc_delta
    if _enc_dt.value():
        _enc_delta += 1
    else:
        _enc_delta -= 1

_enc_clk.irq(trigger=Pin.IRQ_FALLING, handler=_enc_isr)

def encoder_delta():
    global _enc_delta
    d = _enc_delta
    _enc_delta = 0
    return d

# --- Debounce helpers ---

_DEBOUNCE_MS = 50

# --- Encoder button (IRQ on SW, both edges) ---

_enc_sw = Pin(4, Pin.IN, Pin.PULL_UP)
_enc_sw_state = 1
_enc_sw_last_ms = 0
_enc_pressed = False
_enc_released = False

def _enc_sw_isr(pin):
    global _enc_sw_state, _enc_sw_last_ms, _enc_pressed, _enc_released
    now = time.ticks_ms()
    if time.ticks_diff(now, _enc_sw_last_ms) < _DEBOUNCE_MS:
        return
    val = pin.value()
    if val != _enc_sw_state:
        _enc_sw_state = val
        _enc_sw_last_ms = now
        if val == 0:
            _enc_pressed = True
        else:
            _enc_released = True

_enc_sw.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=_enc_sw_isr)

def encoder_clicked():
    global _enc_pressed
    if _enc_pressed:
        _enc_pressed = False
        return True
    return False

def encoder_released():
    global _enc_released
    if _enc_released:
        _enc_released = False
        return True
    return False

# --- Aux button (IRQ, both edges) ---

_aux_btn = Pin(11, Pin.IN, Pin.PULL_UP)
_aux_state = 1
_aux_last_ms = 0
_aux_pressed = False
_aux_released = False

def _aux_isr(pin):
    global _aux_state, _aux_last_ms, _aux_pressed, _aux_released
    now = time.ticks_ms()
    if time.ticks_diff(now, _aux_last_ms) < _DEBOUNCE_MS:
        return
    val = pin.value()
    if val != _aux_state:
        _aux_state = val
        _aux_last_ms = now
        if val == 0:
            _aux_pressed = True
        else:
            _aux_released = True

_aux_btn.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=_aux_isr)

def aux_clicked():
    global _aux_pressed
    if _aux_pressed:
        _aux_pressed = False
        return True
    return False

def aux_released():
    global _aux_released
    if _aux_released:
        _aux_released = False
        return True
    return False