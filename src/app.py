"""
Main application logic for ESP32-S3.

This module contains business logic that should be testable
without requiring actual hardware.
"""

from hardware import LED, Sensor, WiFiConnection  # type: ignore[import-not-found]


class App:
    """Main application class."""

    def __init__(self, led_pin=2, sensor_pin=36):
        """
        Initialize the application.

        Args:
            led_pin: GPIO pin number for LED
            sensor_pin: GPIO pin number for sensor
        """
        self.led = LED(led_pin)
        self.sensor = Sensor(sensor_pin)
        self.wifi = WiFiConnection()
        self._sensor_threshold = 2000
        self._is_running = False

    def start(self):
        """Start the application."""
        self._is_running = True
        self.led.on()

    def stop(self):
        """Stop the application."""
        self._is_running = False
        self.led.off()

    def is_running(self):
        """Check if application is running."""
        return self._is_running

    def check_sensor(self):
        """
        Check sensor reading and update LED accordingly.

        Returns:
            int: Sensor reading value
        """
        value = self.sensor.read()

        if value > self._sensor_threshold:
            self.led.on()
        else:
            self.led.off()

        return value

    def set_sensor_threshold(self, threshold):
        """Set the sensor threshold value."""
        if not 0 <= threshold <= 4095:
            raise ValueError("Threshold must be between 0 and 4095")
        self._sensor_threshold = threshold

    def connect_wifi(self, ssid, password):
        """Connect to WiFi network."""
        self.wifi.connect(ssid, password)
        return self.wifi.is_connected()
