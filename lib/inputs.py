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

# --- Encoder button (IRQ on SW, debounced) ---

_enc_sw = Pin(4, Pin.IN, Pin.PULL_UP)
_enc_clicked = False
_enc_sw_last_ms = 0
_DEBOUNCE_MS = 150

def _enc_sw_isr(pin):
    global _enc_clicked, _enc_sw_last_ms
    if pin.value() == 0:
        now = time.ticks_ms()
        if time.ticks_diff(now, _enc_sw_last_ms) > _DEBOUNCE_MS:
            _enc_clicked = True
            _enc_sw_last_ms = now

_enc_sw.irq(trigger=Pin.IRQ_FALLING, handler=_enc_sw_isr)

def encoder_clicked():
    global _enc_clicked
    if _enc_clicked:
        _enc_clicked = False
        return True
    return False

# --- Aux button (IRQ, debounced) ---

_aux_btn = Pin(11, Pin.IN, Pin.PULL_UP)
_aux_clicked = False
_aux_last_ms = 0

def _aux_isr(pin):
    global _aux_clicked, _aux_last_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, _aux_last_ms) > _DEBOUNCE_MS:
        _aux_clicked = True
        _aux_last_ms = now

_aux_btn.irq(trigger=Pin.IRQ_FALLING, handler=_aux_isr)

def aux_clicked():
    global _aux_clicked
    if _aux_clicked:
        _aux_clicked = False
        return True
    return False