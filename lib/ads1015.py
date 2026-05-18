# ads1015.py — ADS1015 12-bit I2C ADC driver for MicroPython
# Minimal driver for single-shot reads

# Registers
_REG_CONVERSION = 0x00
_REG_CONFIG = 0x01

# Config bits
_OS_SINGLE = 0x8000       # Start single conversion
_MODE_SINGLE = 0x0100     # Single-shot mode
_DR_1600SPS = 0x0080      # 1600 samples/sec (fastest)

# MUX channel selection (single-ended, referenced to GND)
_MUX = {
    0: 0x4000,  # AIN0
    1: 0x5000,  # AIN1
    2: 0x6000,  # AIN2
    3: 0x7000,  # AIN3
}

# PGA gain settings (full-scale voltage)
_PGA = {
    2/3: 0x0000,  # ±6.144V
    1:   0x0200,  # ±4.096V
    2:   0x0400,  # ±2.048V
    4:   0x0600,  # ±1.024V
    8:   0x0800,  # ±0.512V
    16:  0x0A00,  # ±0.256V
}

class ADS1015:
    def __init__(self, i2c, addr=0x48, gain=1):
        self._i2c = i2c
        self._addr = addr
        self._gain = gain
        self._pga = _PGA.get(gain, 0x0200)
        # Full-scale voltage for gain=1 is 4.096V
        # ADS1015 is 12-bit (values 0-2047 for positive)
        self._scale = {
            2/3: 6.144,
            1: 4.096,
            2: 2.048,
            4: 1.024,
            8: 0.512,
            16: 0.256,
        }.get(gain, 4.096) / 2048.0

    def read_raw(self, channel, gain=None):
        """Read raw 12-bit ADC value from channel (0-3). Optional per-read gain override."""
        if channel not in _MUX:
            raise ValueError('Channel must be 0-3')

        pga = _PGA.get(gain, self._pga) if gain is not None else self._pga

        config = (_OS_SINGLE | _MUX[channel] | pga |
                  _MODE_SINGLE | _DR_1600SPS | 0x0003)  # disable comparator

        # Write config to start conversion
        buf = bytes([_REG_CONFIG, (config >> 8) & 0xFF, config & 0xFF])
        self._i2c.writeto(self._addr, buf)

        # Wait for conversion (ADS1015 at 1600SPS = ~0.6ms)
        import time
        time.sleep_ms(1)

        # Read result
        self._i2c.writeto(self._addr, bytes([_REG_CONVERSION]))
        data = self._i2c.readfrom(self._addr, 2)
        raw = (data[0] << 8 | data[1]) >> 4  # 12-bit, left-justified
        if raw > 2047:
            raw -= 4096  # sign extend
        return raw

    def read_voltage(self, channel, gain=None):
        """Read voltage from channel (0-3) in volts. Optional per-read gain override."""
        g = gain if gain is not None else self._gain
        scale = {
            2/3: 6.144,
            1: 4.096,
            2: 2.048,
            4: 1.024,
            8: 0.512,
            16: 0.256,
        }.get(g, 4.096) / 2048.0
        return self.read_raw(channel, gain) * scale