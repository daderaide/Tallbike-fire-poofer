# battery.py — Battery voltage monitor for all three packs
#
# Control box: 1S LiPo via local ADC on GPIO9
#   - Voltage divider ratio: 0.6726
#   - ESP32 ADC with 11dB attenuation, ~0-3.1V range
#
# Relay box (via ADS1015 on I2C):
#   - A2: Igniter battery, 1S LiPo (direct, 0-4.2V, within ADS1015 range at gain=1)
#   - A1: Valve battery, 3S LiPo (through voltage divider, ratio 0.2966)
#
# All voltages reported in mV via modbus registers 4, 5, 6

from hardware import ROLE

# Voltage divider ratios
CONTROL_DIVIDER = 0.6726    # control box: Vbatt * 0.6726 = Vadc
VALVE_DIVIDER = 0.2966      # valve 3S: Vbatt * 0.2966 = Vadc
IGNITER_DIVIDER = 1.0       # igniter 1S: direct connection

# 1S LiPo voltage thresholds (mV)
LIPO_1S_FULL = 4200
LIPO_1S_NOMINAL = 3700
LIPO_1S_LOW = 3400
LIPO_1S_CRITICAL = 3200
LIPO_1S_EMPTY = 3000

# 3S LiPo voltage thresholds (mV)
LIPO_3S_FULL = 12600
LIPO_3S_NOMINAL = 11100
LIPO_3S_LOW = 10200
LIPO_3S_CRITICAL = 9600
LIPO_3S_EMPTY = 9000

# Low battery warning thresholds (mV)
WARN_CONTROL = LIPO_1S_LOW
WARN_IGNITER = LIPO_1S_LOW
WARN_VALVE = LIPO_3S_LOW

_adc = None          # ADS1015 instance (relay box only)
_control_adc = None  # ESP32 ADC (control box only)

# Stored readings (mV)
control_mv = 0
igniter_mv = 0
valve_mv = 0

# Pressure smoothing — 8-sample rolling average
_PRESSURE_SAMPLES = 16
_pressure_buf = []

def init():
    """Initialize ADC hardware for the current role."""
    global _adc, _control_adc
    if ROLE == 'relay':
        from ads1015 import ADS1015
        from hardware import i2c
        _adc = ADS1015(i2c, addr=0x48, gain=1)
    elif ROLE == 'control':
        from hardware import batt_adc
        _control_adc = batt_adc

def read_control():
    """Read control box battery (1S) from local ESP32 ADC. Returns mV."""
    global control_mv
    if _control_adc is None:
        return 0
    # ESP32 ADC with 11dB attenuation: read_uv() returns microvolts at pin
    # Actual battery voltage = pin voltage / divider ratio
    try:
        uv = _control_adc.read_uv()
        pin_mv = uv / 1000
        control_mv = int(pin_mv / CONTROL_DIVIDER)
    except:
        pass
    return control_mv

def read_igniter():
    """Read igniter battery (1S) from ADS1015 channel A2. Returns mV.
    Uses gain=2/3 (±6.144V) since full charge is 4.2V."""
    global igniter_mv
    if _adc is None:
        return 0
    try:
        v = _adc.read_voltage(2, gain=2/3)
        igniter_mv = int((v / IGNITER_DIVIDER) * 1000)
    except:
        pass
    return igniter_mv

def read_valve():
    """Read valve battery (3S) from ADS1015 channel A1. Returns mV."""
    global valve_mv
    if _adc is None:
        return 0
    try:
        v = _adc.read_voltage(1)
        valve_mv = int((v / VALVE_DIVIDER) * 1000)
    except:
        pass
    return valve_mv

def read_pressure_raw():
    """Read pressure sensor from ADS1015 channel A3. Returns smoothed mV at pin.
    Uses gain=2/3 (±6.144V) since sensor outputs 0.5-4.5V.
    8-sample rolling average for noise rejection."""
    if _adc is None:
        return 0
    try:
        v = _adc.read_voltage(3, gain=2/3)
        mv = int(v * 1000)
        _pressure_buf.append(mv)
        if len(_pressure_buf) > _PRESSURE_SAMPLES:
            _pressure_buf.pop(0)
        return sum(_pressure_buf) // len(_pressure_buf)
    except:
        return 0

def percent_1s(mv):
    """Approximate percentage for 1S LiPo from voltage in mV."""
    if mv >= LIPO_1S_FULL:
        return 100
    if mv <= LIPO_1S_EMPTY:
        return 0
    # Linear approximation between empty and full
    return int((mv - LIPO_1S_EMPTY) * 100 / (LIPO_1S_FULL - LIPO_1S_EMPTY))

def percent_3s(mv):
    """Approximate percentage for 3S LiPo from voltage in mV."""
    if mv >= LIPO_3S_FULL:
        return 100
    if mv <= LIPO_3S_EMPTY:
        return 0
    return int((mv - LIPO_3S_EMPTY) * 100 / (LIPO_3S_FULL - LIPO_3S_EMPTY))

def check_warnings():
    """Return list of warning strings for low batteries."""
    warnings = []
    if 0 < control_mv < WARN_CONTROL:
        warnings.append('CTRL BATT LOW')
    if 0 < igniter_mv < WARN_IGNITER:
        warnings.append('IGN BATT LOW')
    if 0 < valve_mv < WARN_VALVE:
        warnings.append('VALVE BATT LOW')
    return warnings