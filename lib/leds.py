# leds.py — NeoPixel ring + aux LED manager (control box only)

import time
from hardware import main_ring, aux_led
import random

NUM_LEDS = 16
# Each LED: [birth_ms, lifetime_ms, hue]
_sparks = [[0, 0, 0.0]] * NUM_LEDS
_sparks_init = False

# Available ring patterns (list will grow)
PATTERNS = ['blink_fade']

# Main ring state
_ring_pattern = 'blink_fade'
_ring_brightness = 100  # 0-100

# Aux LED state
_aux_r = 0
_aux_g = 0
_aux_b = 0
_aux_on = False
_aux_rainbow = False
_aux_brightness = 100  # 0-100

def _time(interval):
    return (time.ticks_ms() / (interval * 65536)) % 1.0

def _triangle(x):
    x = x % 1.0
    return 2.0 * x if x < 0.5 else 2.0 * (1.0 - x)

def _hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)

# Precomputed gamma 2.0 brightness LUT (0-100 -> 0-255 scale factor)
# At 10%: 2, at 25%: 15, at 50%: 63, at 75%: 143, at 100%: 255
_GAMMA_LUT = bytes([int(255 * (i / 100.0) ** 2.0) for i in range(101)])

def _scale(val, brightness):
    if brightness <= 0:
        return 0
    return (val * _GAMMA_LUT[brightness]) >> 8

# --- Main ring controls ---

def set_ring_pattern(pattern):
    global _ring_pattern
    if pattern in PATTERNS:
        _ring_pattern = pattern

def get_ring_pattern():
    return _ring_pattern

def set_ring_brightness(level):
    global _ring_brightness
    _ring_brightness = max(0, min(100, level))

def get_ring_brightness():
    return _ring_brightness

# --- Aux LED controls ---

def set_aux_color(r, g, b):
    global _aux_r, _aux_g, _aux_b, _aux_on, _aux_rainbow
    _aux_r = r
    _aux_g = g
    _aux_b = b
    _aux_on = True
    _aux_rainbow = False

def set_aux_off():
    global _aux_on, _aux_rainbow
    _aux_on = False
    _aux_rainbow = False

def set_aux_rainbow():
    global _aux_on, _aux_rainbow
    _aux_on = True
    _aux_rainbow = True

def set_aux_brightness(level):
    global _aux_brightness
    _aux_brightness = max(0, min(100, level))

def get_aux_brightness():
    return _aux_brightness

# --- Update both strips ---

def update(delta_ms):
    bri = _ring_brightness
    aux_bri = _aux_brightness

    # Aux LED
    if _aux_on:
        if _aux_rainbow:
            hue = _time(0.05)  # slow cycle through full spectrum
            r, g, b = _hsv_to_rgb(hue, 1.0, 1.0)
            aux_led[0] = (_scale(r, aux_bri),
                           _scale(g, aux_bri),
                           _scale(b, aux_bri))
        else:
            aux_led[0] = (_scale(_aux_r, aux_bri),
                           _scale(_aux_g, aux_bri),
                           _scale(_aux_b, aux_bri))
    else:
        aux_led[0] = (0, 0, 0)
    aux_led.write()

    # Main ring
    if bri == 0:
        for i in range(NUM_LEDS):
            main_ring[i] = (0, 0, 0)
        main_ring.write()
        return

    # blink_fade pattern (sparkle with absolute timing)
    if _ring_pattern == 'blink_fade':
        global _sparks_init, _sparks
        now = time.ticks_ms()

        if not _sparks_init:
            _sparks = []
            for i in range(NUM_LEDS):
                lt = 400 + int(random.random() * 1600)  # 400-2000ms lifetime
                born = now - int(random.random() * lt)   # stagger initial births
                h = _time(0.07) + _triangle(i / NUM_LEDS) * 0.2
                _sparks.append([born, lt, h])
            _sparks_init = True

        for i in range(NUM_LEDS):
            born, lt, h = _sparks[i]
            age = time.ticks_diff(now, born)
            if age >= lt:
                # Respawn
                lt = 400 + int(random.random() * 1600)
                h = _time(0.07) + _triangle(i / NUM_LEDS) * 0.2
                _sparks[i] = [now, lt, h]
                age = 0

            # Fade: bright at birth, dims to zero over lifetime
            frac = 1.0 - (age / lt)
            v = frac * frac  # quadratic ease-out for nice tail
            r, g, b = _hsv_to_rgb(h, 1.0, v)
            main_ring[i] = (_scale(r, bri), _scale(g, bri), _scale(b, bri))
        main_ring.write()