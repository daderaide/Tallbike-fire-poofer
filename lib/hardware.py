"""
Hardware abstraction layer for Control Box and Relay Box for Tallbike Fire Poofer

This module provides abstractions for lower level hardware functions that are boards and pin specific for each box
"""

# hardware.py — Hardware abstraction layer
# Reads role.txt to determine which box this is running on

from machine import Pin, I2C, ADC
import neopixel

def get_role():
    with open('role.txt', 'r') as f:
        return f.read().strip()

ROLE = get_role()

# --- Shared (both boxes) ---


# --- Role-specific hardware ---
if ROLE == 'control':
    i2c = I2C(0, sda=Pin(13), scl=Pin(14), freq=400000)

    # Buttons
    main_btn = Pin(7, Pin.IN, Pin.PULL_UP)
    aux_btn = Pin(11, Pin.IN, Pin.PULL_UP)

    # Encoder
    enc_clk = Pin(6, Pin.IN)
    enc_dt = Pin(5, Pin.IN)
    enc_sw = Pin(4, Pin.IN, Pin.PULL_UP)

    # Battery ADC
    batt_adc = ADC(Pin(9))
    batt_adc.atten(ADC.ATTN_11DB)

    # NeoPixels
    main_ring = neopixel.NeoPixel(Pin(15), 16)
    aux_led = neopixel.NeoPixel(Pin(10), 1)

elif ROLE == 'relay':
    i2c = I2C(0, sda=Pin(2), scl=Pin(1), freq=100000)

    # Igniter relay
    igniter = Pin(38, Pin.OUT, value=0)