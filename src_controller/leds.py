"""
NeoPixel control for main button ring (16 LEDs) and aux button (1 LED).
"""

try:
    from machine import Pin
    import neopixel
    import random
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    Pin = None
    neopixel = None
    random = None

from hardware import PIN_MAIN_NEOPIXEL, PIN_AUX_NEOPIXEL

# Global brightness (0.0 - 1.0)
BRIGHTNESS = 0.25


class LEDManager:
    """Manages NeoPixel LEDs on main ring and aux button."""

    MAIN_RING_COUNT = 16
    AUX_LED_COUNT = 1

    def __init__(self):
        if MICROPYTHON:
            self._main_ring = neopixel.NeoPixel(
                Pin(PIN_MAIN_NEOPIXEL, Pin.OUT),
                self.MAIN_RING_COUNT
            )
            self._aux_led = neopixel.NeoPixel(
                Pin(PIN_AUX_NEOPIXEL, Pin.OUT),
                self.AUX_LED_COUNT
            )
        else:
            self._main_ring = None
            self._aux_led = None

    def set_random_colors(self):
        """Set all LEDs to random colors at configured brightness."""
        if not MICROPYTHON:
            return

        # Random colors for main ring
        for i in range(self.MAIN_RING_COUNT):
            r = int(random.randint(0, 255) * BRIGHTNESS)
            g = int(random.randint(0, 255) * BRIGHTNESS)
            b = int(random.randint(0, 255) * BRIGHTNESS)
            self._main_ring[i] = (r, g, b)
        self._main_ring.write()

        # Random color for aux LED
        r = int(random.randint(0, 255) * BRIGHTNESS)
        g = int(random.randint(0, 255) * BRIGHTNESS)
        b = int(random.randint(0, 255) * BRIGHTNESS)
        self._aux_led[0] = (r, g, b)
        self._aux_led.write()

    def set_main_ring(self, colors: list):
        """
        Set individual LED colors on main ring.

        Args:
            colors: List of (r, g, b) tuples, one per LED.
                    Values should be 0-255, brightness applied automatically.
        """
        if not MICROPYTHON:
            return

        for i, color in enumerate(colors):
            if i >= self.MAIN_RING_COUNT:
                break
            r = int(color[0] * BRIGHTNESS)
            g = int(color[1] * BRIGHTNESS)
            b = int(color[2] * BRIGHTNESS)
            self._main_ring[i] = (r, g, b)
        self._main_ring.write()

    def set_main_ring_solid(self, color: tuple):
        """
        Set all main ring LEDs to the same color.

        Args:
            color: (r, g, b) tuple, values 0-255.
        """
        if not MICROPYTHON:
            return

        r = int(color[0] * BRIGHTNESS)
        g = int(color[1] * BRIGHTNESS)
        b = int(color[2] * BRIGHTNESS)
        for i in range(self.MAIN_RING_COUNT):
            self._main_ring[i] = (r, g, b)
        self._main_ring.write()

    def set_aux_led(self, color: tuple):
        """
        Set aux button LED color.

        Args:
            color: (r, g, b) tuple, values 0-255.
        """
        if not MICROPYTHON:
            return

        r = int(color[0] * BRIGHTNESS)
        g = int(color[1] * BRIGHTNESS)
        b = int(color[2] * BRIGHTNESS)
        self._aux_led[0] = (r, g, b)
        self._aux_led.write()

    def all_off(self):
        """Turn off all LEDs."""
        if not MICROPYTHON:
            return

        for i in range(self.MAIN_RING_COUNT):
            self._main_ring[i] = (0, 0, 0)
        self._main_ring.write()

        self._aux_led[0] = (0, 0, 0)
        self._aux_led.write()
