"""
Hardware abstraction layer for Control Box ESP32-S3.

This module provides abstractions over MicroPython hardware modules.
The Control Box is the master device that sends commands to the Relay Box.
"""

try:
    from machine import I2C, UART, Pin, ADC
    import time
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    I2C = None
    UART = None
    Pin = None
    ADC = None
    time = None

# =============================================================================
# Pin Constants
# =============================================================================

# I2C (LCD)
PIN_SDA = 13
PIN_SCL = 14
I2C_FREQ = 400000

# UART / RS-485
PIN_UART_TX = 17
PIN_UART_RX = 18
PIN_RS485_DE_RE = 8
UART_BAUD = 9600

# Rotary Encoder
PIN_ENC_CLK = 6   # External 10k pull-up
PIN_ENC_DT = 5    # External 10k pull-up
PIN_ENC_SW = 4    # Internal pull-up

# Buttons
PIN_MAIN_BTN = 7    # Internal pull-up
PIN_AUX_BTN = 11    # Internal pull-up

# NeoPixels
PIN_MAIN_NEOPIXEL = 15  # 16 LEDs ring
PIN_AUX_NEOPIXEL = 10   # 1 LED

# Battery ADC
PIN_BATTERY_ADC = 9     # ADC1_CH8, 11dB attenuation
BATTERY_DIVIDER_RATIO = 0.6726

# I2C Addresses
I2C_ADDR_LCD = 0x27


# =============================================================================
# Hardware Classes
# =============================================================================

class RS485:
    """
    UART1 + DE/RE control on GPIO8.

    Key difference from Relay Box: This is the MASTER, so we default to
    drive enabled (DE/RE HIGH) and only switch to receive when waiting
    for a response.
    """

    def __init__(self):
        if MICROPYTHON:
            self._uart = UART(1, baudrate=UART_BAUD, tx=PIN_UART_TX, rx=PIN_UART_RX)
            # Start with DE/RE LOW during boot, will enable after 3s delay
            self._de_re = Pin(PIN_RS485_DE_RE, Pin.OUT, value=0)
            self._drive_enabled = False
        else:
            self._uart = None
            self._de_re = None
            self._drive_enabled = False

    def enable_drive(self):
        """Enable drive mode (call after 3s boot delay)."""
        if MICROPYTHON:
            self._de_re.value(1)
        self._drive_enabled = True

    def send_and_receive(self, data: bytes, timeout_ms: int = 1000) -> bytes | None:
        """
        Send data and wait for response.

        1. Send data (already in drive mode)
        2. Wait for TX to complete
        3. Switch to receive mode
        4. Wait for response with timeout
        5. Switch back to drive mode
        """
        if not MICROPYTHON:
            return None

        if not self._drive_enabled:
            return None

        # Send data (already in drive mode)
        self._uart.write(data)

        # Wait for transmission to complete
        # At 9600 baud, each byte takes ~1ms
        time.sleep_ms(1 + len(data))

        # Switch to receive mode
        self._de_re.value(0)

        # Wait for response with timeout
        start = time.ticks_ms()
        while not self._uart.any():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                # Timeout - back to drive mode
                self._de_re.value(1)
                return None
            time.sleep_ms(1)

        # Small delay to allow full message to arrive
        time.sleep_ms(10)

        # Read all available data
        response = self._uart.read()

        # Back to drive mode
        self._de_re.value(1)
        return response


class BatteryADC:
    """Read local battery voltage via ADC with 11dB attenuation."""

    def __init__(self):
        if MICROPYTHON:
            self._adc = ADC(Pin(PIN_BATTERY_ADC))
            self._adc.atten(ADC.ATTN_11DB)  # 0-3.3V range
            self._adc.width(ADC.WIDTH_12BIT)  # 0-4095
        else:
            self._adc = None

    def read_raw(self) -> int:
        """Read raw ADC value (0-4095)."""
        if not MICROPYTHON:
            return 0
        return self._adc.read()

    def read_voltage(self) -> float:
        """Read actual battery voltage accounting for divider."""
        raw = self.read_raw()
        # ADC voltage (0-3.3V mapped to 0-4095)
        adc_voltage = (raw / 4095.0) * 3.3
        # Actual battery voltage accounting for divider
        actual_voltage = adc_voltage / BATTERY_DIVIDER_RATIO
        return actual_voltage


class Hardware:
    """Main hardware container - initializes all hardware."""

    def __init__(self):
        # Initialize I2C
        if MICROPYTHON:
            self.i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=I2C_FREQ)
        else:
            self.i2c = None

        # Initialize RS-485 (drive enabled later after boot delay)
        self.rs485 = RS485()

        # Initialize battery ADC
        self.battery_adc = BatteryADC()
