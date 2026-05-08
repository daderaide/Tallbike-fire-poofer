"""
Unit tests for the application logic.

These tests run on your host Python environment using mocks
for the hardware abstraction layer.
"""

import pytest
from app import App
from hardware import LED, Sensor, WiFiConnection


class TestApp:
    """Test cases for the App class."""
    
    def test_app_initialization(self):
        """Test that App initializes correctly."""
        app = App(led_pin=2, sensor_pin=36)
        assert app.led is not None
        assert app.sensor is not None
        assert app.wifi is not None
        assert not app.is_running()
    
    def test_start_stop(self):
        """Test starting and stopping the application."""
        app = App()
        
        app.start()
        assert app.is_running()
        assert app.led.is_on
        
        app.stop()
        assert not app.is_running()
        assert not app.led.is_on
    
    def test_check_sensor_above_threshold(self):
        """Test sensor check when value is above threshold."""
        app = App()
        
        # Mock the sensor to return a high value
        # Since we're on host Python, hardware abstraction returns mock values
        # In a real scenario, you might want to use dependency injection
        # or mock the sensor object more explicitly
        
        app.set_sensor_threshold(2000)
        # Default mock sensor returns 2048, which is above threshold
        value = app.check_sensor()
        
        assert value == 2048  # Mock sensor default value
        assert app.led.is_on  # Should turn on LED
    
    def test_check_sensor_below_threshold(self):
        """Test sensor check when value is below threshold."""
        app = App()
        
        # Set threshold high so mock value (2048) is below it
        app.set_sensor_threshold(3000)
        value = app.check_sensor()
        
        assert value == 2048
        assert not app.led.is_on  # Should turn off LED
    
    def test_set_sensor_threshold_valid(self):
        """Test setting a valid sensor threshold."""
        app = App()
        
        app.set_sensor_threshold(2500)
        assert app._sensor_threshold == 2500
    
    def test_set_sensor_threshold_invalid_too_high(self):
        """Test setting an invalid sensor threshold (too high)."""
        app = App()
        
        with pytest.raises(ValueError, match="Threshold must be between 0 and 4095"):
            app.set_sensor_threshold(5000)
    
    def test_set_sensor_threshold_invalid_too_low(self):
        """Test setting an invalid sensor threshold (too low)."""
        app = App()
        
        with pytest.raises(ValueError, match="Threshold must be between 0 and 4095"):
            app.set_sensor_threshold(-1)
    
    def test_connect_wifi(self):
        """Test WiFi connection."""
        app = App()
        
        # On host Python, WiFi mock should work
        result = app.connect_wifi("test_ssid", "test_password")
        assert result is True
        assert app.wifi.is_connected()
        
        app.wifi.disconnect()
        assert not app.wifi.is_connected()


class TestHardwareAbstractions:
    """Test cases for hardware abstraction layer."""
    
    def test_led_control(self):
        """Test LED control without actual hardware."""
        led = LED(2)
        
        assert not led.is_on
        led.on()
        assert led.is_on
        led.off()
        assert not led.is_on
    
    def test_sensor_reading(self):
        """Test sensor reading without actual hardware."""
        sensor = Sensor(36)
        
        # Mock sensor returns default value on host Python
        value = sensor.read()
        assert isinstance(value, int)
        assert 0 <= value <= 4095
    
    def test_wifi_connection(self):
        """Test WiFi connection without actual hardware."""
        wifi = WiFiConnection()
        
        assert not wifi.is_connected()
        wifi.connect("test_ssid", "test_password")
        assert wifi.is_connected()
        wifi.disconnect()
        assert not wifi.is_connected()


# Example of how to use pytest-mock for more advanced mocking
class TestAppWithPytestMock:
    """Examples using pytest-mock for more advanced test scenarios."""
    
    def test_sensor_with_custom_mock(self, mocker):
        """Example of mocking sensor with custom return value."""
        app = App()
        
        # Mock the sensor's read method to return specific values
        mocker.patch.object(app.sensor, 'read', return_value=3000)
        
        app.set_sensor_threshold(2500)
        value = app.check_sensor()
        
        assert value == 3000
        assert app.led.is_on
    
    def test_multiple_sensor_readings(self, mocker):
        """Example of mocking multiple sensor readings."""
        app = App()
        
        # Mock sensor to return different values on subsequent calls
        mock_read = mocker.patch.object(app.sensor, 'read', side_effect=[1000, 3000, 2000])
        
        app.set_sensor_threshold(2500)
        
        # First reading below threshold
        value1 = app.check_sensor()
        assert value1 == 1000
        assert not app.led.is_on
        
        # Second reading above threshold
        value2 = app.check_sensor()
        assert value2 == 3000
        assert app.led.is_on
        
        # Third reading below threshold again
        value3 = app.check_sensor()
        assert value3 == 2000
        assert not app.led.is_on
