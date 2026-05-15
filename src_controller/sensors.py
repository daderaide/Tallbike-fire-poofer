"""
Battery voltage monitor for the Control Box's local 1S battery.
"""

from hardware import BatteryADC


class BatteryMonitor:
    """Monitor the Control Box's local 1S LiPo battery."""

    def __init__(self, battery_adc: BatteryADC):
        self._adc = battery_adc

    def read_voltage(self) -> float:
        """
        Read actual battery voltage (0-4.2V range for 1S LiPo).

        Returns the voltage after accounting for the divider ratio.
        """
        return self._adc.read_voltage()

    def read_percentage(self) -> int:
        """
        Convert voltage to approximate percentage.

        Uses a simple linear approximation:
        - 4.2V = 100%
        - 3.0V = 0%
        """
        voltage = self.read_voltage()

        # Linear mapping from 3.0V-4.2V to 0-100%
        if voltage >= 4.2:
            return 100
        elif voltage <= 3.0:
            return 0
        else:
            percentage = int(((voltage - 3.0) / 1.2) * 100)
            return max(0, min(100, percentage))
