"""
LCD display manager with placeholder implementations.

This module handles the 20x4 I2C LCD display for showing system status.
The actual LCD driver implementation is left as a placeholder.
"""

from hardware import I2C_ADDR_LCD


class DisplayManager:
    """
    Manages the 20x4 I2C LCD display.

    Display layout:
        Row 0: Pressure + uptime
        Row 1: Battery voltages (control, igniter, valve)
        Row 2: Button status
        Row 3: Encoder position
    """

    ROWS = 4
    COLS = 20

    def __init__(self, i2c):
        # Placeholder: Would initialize LCD at I2C_ADDR_LCD
        self._i2c = i2c
        self._lcd = None  # Placeholder for actual LCD driver

        # State to display
        self._pressure_psi = 0.0
        self._control_battery_v = 0.0
        self._igniter_battery_mv = 0
        self._valve_battery_mv = 0
        self._uptime_ms = 0
        self._main_btn_pressed = False
        self._aux_btn_pressed = False
        self._encoder_pos = 0
        self._connected = False

    def update_pressure(self, psi: float):
        """Update pressure reading and refresh display."""
        self._pressure_psi = psi
        self._refresh_display()

    def update_control_battery(self, voltage: float):
        """Update control box battery voltage and refresh display."""
        self._control_battery_v = voltage
        self._refresh_display()

    def update_remote_batteries(self, igniter_mv: int, valve_mv: int):
        """Update remote battery readings and refresh display."""
        self._igniter_battery_mv = igniter_mv
        self._valve_battery_mv = valve_mv
        self._refresh_display()

    def update_uptime(self, ms: int):
        """Update uptime and refresh display."""
        self._uptime_ms = ms
        self._refresh_display()

    def update_inputs(self, main_btn: bool, aux_btn: bool, encoder_pos: int):
        """Update input states and refresh display."""
        self._main_btn_pressed = main_btn
        self._aux_btn_pressed = aux_btn
        self._encoder_pos = encoder_pos
        self._refresh_display()

    def update_connection_status(self, connected: bool):
        """Update connection status and refresh display."""
        self._connected = connected
        self._refresh_display()

    def _refresh_display(self):
        """
        Format and write all data to LCD.

        Placeholder implementation - actual LCD writes would go here.
        """
        # Row 0: Pressure + uptime
        uptime_sec = self._uptime_ms // 1000
        uptime_min = uptime_sec // 60
        uptime_sec = uptime_sec % 60
        row0 = f"P:{self._pressure_psi:5.1f}psi  {uptime_min:02d}:{uptime_sec:02d}"

        # Row 1: Battery voltages
        ctrl_v = self._control_battery_v
        ign_v = self._igniter_battery_mv / 1000.0 if self._igniter_battery_mv else 0.0
        valve_v = self._valve_battery_mv / 1000.0 if self._valve_battery_mv else 0.0
        row1 = f"C:{ctrl_v:.1f}V I:{ign_v:.1f}V V:{valve_v:.1f}V"

        # Row 2: Button status + connection
        main_str = "MAIN" if self._main_btn_pressed else "----"
        aux_str = "AUX" if self._aux_btn_pressed else "---"
        conn_str = "OK" if self._connected else "--"
        row2 = f"BTN:{main_str} {aux_str} [{conn_str}]"

        # Row 3: Encoder position
        row3 = f"ENC:{self._encoder_pos:+4d}"

        # Placeholder: Would write to actual LCD
        # self._write_line(0, row0)
        # self._write_line(1, row1)
        # self._write_line(2, row2)
        # self._write_line(3, row3)

    def _write_line(self, row: int, text: str):
        """
        Write a line of text to the LCD.

        Placeholder implementation.
        """
        # Pad or truncate to COLS width
        text = text[:self.COLS].ljust(self.COLS)

        # Placeholder: Would write to LCD at row position
        # self._lcd.move_to(0, row)
        # self._lcd.putstr(text)
        pass

    def clear(self):
        """Clear the LCD display."""
        # Placeholder: Would clear actual LCD
        # self._lcd.clear()
        pass

    def show_startup_message(self):
        """Show startup message during boot."""
        # Placeholder: Would display startup message
        # self._write_line(0, "  Control Box v1.0  ")
        # self._write_line(1, "                    ")
        # self._write_line(2, "   Initializing...  ")
        # self._write_line(3, "                    ")
        pass
