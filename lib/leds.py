# leds.py — NeoPixel ring + aux LED manager (control box only)

import time
from hardware import main_ring, aux_led
import random

NUM_LEDS = 16
vals = [0.0] * NUM_LEDS
hues = [0.0] * NUM_LEDS

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

def _scale(val, brightness):
    return (val * brightness) // 100

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
    global _aux_r, _aux_g, _aux_b, _aux_on
    _aux_r = r
    _aux_g = g
    _aux_b = b
    _aux_on = True

def set_aux_off():
    global _aux_on
    _aux_on = False

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

    # blink_fade pattern (the original sparkle)
    if _ring_pattern == 'blink_fade':
        for i in range(NUM_LEDS):
            vals[i] -= 0.005 * delta_ms * 0.1
            if vals[i] <= 0:
                vals[i] = random.random()
                hues[i] = _time(0.07) + _triangle(i / NUM_LEDS) * 0.2

        for i in range(NUM_LEDS):
            v = vals[i] * vals[i]
            r, g, b = _hsv_to_rgb(hues[i], 1.0, v)
            main_ring[i] = (_scale(r, bri), _scale(g, bri), _scale(b, bri))
        main_ring.write()