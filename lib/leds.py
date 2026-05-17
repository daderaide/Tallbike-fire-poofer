# leds.py — NeoPixel ring manager (control box only)

import time
from hardware import main_ring
import random

NUM_LEDS = 16
vals = [0.0] * NUM_LEDS
hues = [0.0] * NUM_LEDS

# Mode: 'sparkle', 'solid', 'off'
_mode = 'sparkle'
_solid_r = 0
_solid_g = 0
_solid_b = 0

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

def set_color(r, g, b):
    global _mode, _solid_r, _solid_g, _solid_b
    _mode = 'solid'
    _solid_r = r
    _solid_g = g
    _solid_b = b

def set_off():
    global _mode
    _mode = 'off'

def set_sparkle():
    global _mode
    _mode = 'sparkle'

def update(delta_ms):
    if _mode == 'off':
        for i in range(NUM_LEDS):
            main_ring[i] = (0, 0, 0)
        main_ring.write()
        return

    if _mode == 'solid':
        for i in range(NUM_LEDS):
            main_ring[i] = (_solid_r, _solid_g, _solid_b)
        main_ring.write()
        return

    # Sparkle mode (default)
    for i in range(NUM_LEDS):
        vals[i] -= 0.005 * delta_ms * 0.1
        if vals[i] <= 0:
            vals[i] = random.random()
            hues[i] = _time(0.07) + _triangle(i / NUM_LEDS) * 0.2

    for i in range(NUM_LEDS):
        v = vals[i] * vals[i]
        r, g, b = _hsv_to_rgb(hues[i], 1.0, v)
        main_ring[i] = (r, g, b)
    main_ring.write()