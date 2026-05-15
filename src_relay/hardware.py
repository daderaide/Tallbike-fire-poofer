"""
Hardware abstraction layer for Relay Box ESP32-S3.

This module provides abstractions over MicroPython hardware modules,
making them easier to mock in tests.
"""

try:
    from machine import I2C, UART, Pin
    import time
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    I2C = None
    UART = None
    Pin = None
    time = None

# =============================================================================
# Pin Constants
# =============================================================================

# I2C
PIN_SDA = 1
PIN_SCL = 2
I2C_FREQ = 400000

# UART / RS-485
PIN_UART_TX = 17
PIN_UART_RX = 18
PIN_RS485_DE_RE = 8
UART_BAUD = 9600

# Relays
PIN_IGNITER_RELAY = 38

# I2C Addresses
I2C_ADDR_RELAY_BOARD = 0x3F
I2C_ADDR_ADS1015 = 0x48


# =============================================================================
# Hardware Classes
# =============================================================================

class RelayBoard:
    """PCF8574A 8-relay module at 0x3F (active-low)."""

    def __init__(self, i2c):
        self._i2c = i2c
        self._addr = I2C_ADDR_RELAY_BOARD
        self._state = 0xFF  # All relays OFF (active-low)
        self.all_off()

    def set_relay(self, index: int, state: bool):
        """Set relay by index (0-7). True = ON, False = OFF."""
        if not 0 <= index <= 7:
            raise ValueError("Relay index must be 0-7")
        # Active-low: clear bit to turn ON, set bit to turn OFF
        if state:
            self._state &= ~(1 << index)  # Clear bit (ON)
        else:
            self._state |= (1 << index)   # Set bit (OFF)
        self._write_state()

    def set_all(self, bitmask: int):
        """Set all relays with bitmask. Active-low: 0=ON, 1=OFF."""
        self._state = bitmask & 0xFF
        self._write_state()

    def get_state(self) -> int:
        """Get current relay state bitmask."""
        return self._state

    def all_off(self):
        """Turn all relays OFF (writes 0xFF)."""
        self._state = 0xFF
        self._write_state()

    def _write_state(self):
        """Write current state to I2C device."""
        if MICROPYTHON:
            self._i2c.writeto(self._addr, bytes([self._state]))


class IgniterRelay:
    """Single GPIO relay on GPIO38 (active high, init LOW)."""

    def __init__(self):
        self._is_on = False
        if MICROPYTHON:
            self._pin = Pin(PIN_IGNITER_RELAY, Pin.OUT, value=0)
        else:
            self._pin = None

    def on(self):
        """Turn igniter relay ON."""
        if MICROPYTHON:
            self._pin.value(1)
        self._is_on = True

    def off(self):
        """Turn igniter relay OFF."""
        if MICROPYTHON:
            self._pin.value(0)
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Check if igniter relay is ON."""
        return self._is_on


class ADS1015:
    """4-channel 12-bit ADC at 0x48."""

    # ADS1015 registers
    _REG_CONVERSION = 0x00
    _REG_CONFIG = 0x01

    # Config register bits
    _OS_SINGLE = 0x8000      # Start single conversion
    _MUX_BASE = 0x4000       # Single-ended AIN0
    _PGA_4_096V = 0x0200     # Gain = 1, +/- 4.096V
    _MODE_SINGLE = 0x0100    # Single-shot mode
    _DR_1600SPS = 0x0080     # 1600 samples/sec
    _COMP_DISABLE = 0x0003   # Disable comparator

    def __init__(self, i2c):
        self._i2c = i2c
        self._addr = I2C_ADDR_ADS1015

    def read_channel(self, channel: int) -> int:
        """Read raw 12-bit value from channel (0-3)."""
        if not 0 <= channel <= 3:
            raise ValueError("Channel must be 0-3")

        if not MICROPYTHON:
            return 0

        # Configure for single-ended read on specified channel
        mux = (0x4 + channel) << 12  # MUX[14:12]: AINx to GND
        config = (
            self._OS_SINGLE |
            mux |
            self._PGA_4_096V |
            self._MODE_SINGLE |
            self._DR_1600SPS |
            self._COMP_DISABLE
        )

        # Write config register
        config_bytes = bytes([self._REG_CONFIG, (config >> 8) & 0xFF, config & 0xFF])
        self._i2c.writeto(self._addr, config_bytes)

        # Wait for conversion (ADS1015 is fast, ~1ms at 1600SPS)
        time.sleep_ms(2)

        # Read conversion result
        self._i2c.writeto(self._addr, bytes([self._REG_CONVERSION]))
        data = self._i2c.readfrom(self._addr, 2)

        # Convert to 12-bit value (upper 12 bits of 16-bit result)
        raw = ((data[0] << 8) | data[1]) >> 4
        return raw

    def read_voltage(self, channel: int) -> float:
        """Read voltage from channel (0-3). Gain=1, +/-4.096V range."""
        raw = self.read_channel(channel)
        # 12-bit signed value, but single-ended is always positive
        # Full scale is 2048 counts = 4.096V
        voltage = (raw / 2048.0) * 4.096
        return voltage


class PressureSensor:
    """Propane pressure sensor on ADS1015 A0."""

    def __init__(self, adc: ADS1015):
        self._adc = adc
        self._channel = 0

    def read_psi(self) -> float:
        """Read pressure in PSI (0-500 range)."""
        # Sensor outputs 0.5V at 0 PSI, 4.5V at 500 PSI
        voltage = self._adc.read_voltage(self._channel)
        psi = ((voltage - 0.5) / 4.0) * 500.0
        # Clamp to valid range
        psi = max(0.0, min(500.0, psi))
        return psi

    def read_raw(self) -> int:
        """Read raw ADC value."""
        return self._adc.read_channel(self._channel)


class BatteryMonitor:
    """Battery monitors on ADS1015 A1/A2."""

    def __init__(self, adc: ADS1015):
        self._adc = adc

    def read_igniter_voltage(self) -> float:
        """Read igniter battery voltage (A1: 1S direct, 0-4.2V)."""
        return self._adc.read_voltage(1)

    def read_valve_voltage(self) -> float:
        """Read valve battery voltage (A2: 3S with divider, 0-12.6V)."""
        # Voltage divider ratio: 0.2966
        reading = self._adc.read_voltage(2)
        actual = reading / 0.2966
        return actual


class RS485:
    """UART1 + DE/RE control on GPIO8."""

    def __init__(self):
        if MICROPYTHON:
            self._uart = UART(1, baudrate=UART_BAUD, tx=PIN_UART_TX, rx=PIN_UART_RX)
            self._de_re = Pin(PIN_RS485_DE_RE, Pin.OUT, value=0)  # Start in receive mode
        else:
            self._uart = None
            self._de_re = None

    def send(self, data: bytes):
        """Send data over RS-485."""
        if not MICROPYTHON:
            return

        # Enable transmitter
        self._de_re.value(1)
        time.sleep_us(100)  # Small delay for driver to enable

        # Send data
        self._uart.write(data)

        # Wait for transmission to complete
        # At 9600 baud, each byte takes ~1ms
        time.sleep_ms(1 + len(data))

        # Return to receive mode
        self._de_re.value(0)

    def receive(self, timeout_ms: int = 1000) -> bytes | None:
        """Receive data from RS-485. Returns None if no data."""
        if not MICROPYTHON:
            return None

        # Wait for data with timeout
        start = time.ticks_ms()
        while not self._uart.any():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                return None
            time.sleep_ms(1)

        # Small delay to allow full message to arrive
        time.sleep_ms(10)

        # Read all available data
        data = self._uart.read()
        return data


class Hardware:
    """Main hardware container - initializes all hardware."""

    def __init__(self):
        # Initialize I2C
        if MICROPYTHON:
            self.i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=I2C_FREQ)
        else:
            self.i2c = None

        # Initialize UART (handled by RS485 class)
        self.uart = None

        # Initialize hardware components
        self.relay_board = RelayBoard(self.i2c)
        self.igniter = IgniterRelay()
        self.adc = ADS1015(self.i2c)
        self.pressure = PressureSensor(self.adc)
        self.battery = BatteryMonitor(self.adc)
        self.rs485 = RS485()
