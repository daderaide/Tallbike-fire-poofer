"""
Hardware abstraction layer for ESP32-S3.

This module provides abstractions over MicroPython hardware modules,
making them easier to mock in tests.
"""

try:
    # MicroPython imports (will fail on host Python, that's OK)
    import machine  # type: ignore[import-not-found]
    from machine import ADC, I2C, SPI, Pin  # type: ignore[import-not-found]
    MICROPYTHON = True
except ImportError:
    # For testing on host Python
    MICROPYTHON = False
    machine = None
    Pin = None  # type: ignore[assignment]
    ADC = None  # type: ignore[assignment]
    I2C = None  # type: ignore[assignment]
    SPI = None  # type: ignore[assignment]


class LED:
    """LED control abstraction."""

    def __init__(self, pin_number):
        if MICROPYTHON:
            self._pin = Pin(pin_number, Pin.OUT)
        else:
            self._pin = None
            self._pin_number = pin_number
            self._state = False

    def on(self):
        """Turn LED on."""
        if MICROPYTHON:
            self._pin.on()
        else:
            self._state = True

    def off(self):
        """Turn LED off."""
        if MICROPYTHON:
            self._pin.off()
        else:
            self._state = False

    @property
    def is_on(self):
        """Check if LED is on."""
        if MICROPYTHON:
            return self._pin.value() == 1
        else:
            return self._state


class Sensor:
    """Sensor reading abstraction."""

    def __init__(self, pin_number):
        if MICROPYTHON:
            self._adc = ADC(Pin(pin_number))
            self._adc.atten(ADC.ATTN_11DB)  # 0-3.3V range
        else:
            self._adc = None
            self._pin_number = pin_number

    def read(self):
        """Read sensor value (0-4095 for 12-bit ADC)."""
        if MICROPYTHON:
            return self._adc.read()
        else:
            # Return mock value for testing
            return 2048


class WiFiConnection:
    """WiFi connection abstraction."""

    def __init__(self):
        if MICROPYTHON:
            import network  # type: ignore[import-not-found]
            self._wlan = network.WLAN(network.STA_IF)
        else:
            self._wlan = None
            self._connected = False

    def connect(self, ssid, password):
        """Connect to WiFi network."""
        if MICROPYTHON:
            self._wlan.active(True)
            self._wlan.connect(ssid, password)
            # In real code, you'd wait and check connection status
        else:
            self._connected = True

    def is_connected(self):
        """Check if WiFi is connected."""
        if MICROPYTHON:
            return self._wlan.isconnected()
        else:
            return self._connected

    def disconnect(self):
        """Disconnect from WiFi."""
        if MICROPYTHON:
            self._wlan.disconnect()
            self._wlan.active(False)
        else:
            self._connected = False
