"""
RS-485 communication protocol handler for Relay Box.

This module handles command/response protocol over RS-485.
"""

from hardware import Hardware
from macros import MacroRunner

# =============================================================================
# Protocol Constants
# =============================================================================

# Commands (1 byte)
CMD_PING = 0x01
CMD_GET_SENSOR = 0x02
CMD_RUN_MACRO = 0x03
CMD_STOP = 0x04

# Sensor IDs (for GET_SENSOR)
SENSOR_PRESSURE = 0x00
SENSOR_IGNITER_BATTERY = 0x01
SENSOR_VALVE_BATTERY = 0x02

# Responses (1 byte header)
RESP_ACK = 0x06
RESP_NACK = 0x15
RESP_DATA = 0x02
RESP_NO_DATA = 0x03
RESP_BUSY = 0x07


# =============================================================================
# Command Handler
# =============================================================================

class CommandHandler:
    """Handles RS-485 commands and generates responses."""

    def __init__(self, hardware: Hardware):
        self._hw = hardware
        self._macro_runner = MacroRunner(hardware.relay_board, hardware.igniter)

    def run(self):
        """Main loop: listen, parse, execute, respond."""
        while True:
            # Advance macro state if running
            self._macro_runner.tick()

            # Wait for incoming data (short timeout to keep ticking)
            data = self._hw.rs485.receive(timeout_ms=100)
            if data is None or len(data) == 0:
                continue

            # Parse and handle command
            try:
                cmd, params = self._parse_command(data)
                response = self._execute_command(cmd, params)
                self._send_response(response)
            except Exception:
                # Send NACK on any error
                self._send_response(bytes([RESP_NACK]))

    def _parse_command(self, data: bytes) -> tuple:
        """Parse command from received data. Returns (cmd_byte, params_bytes)."""
        if len(data) < 1:
            raise ValueError("Empty command")
        cmd = data[0]
        params = data[1:] if len(data) > 1 else b''
        return (cmd, params)

    def _execute_command(self, cmd: int, params: bytes) -> bytes:
        """Execute command and return response bytes."""
        # STOP always executes immediately
        if cmd == CMD_STOP:
            return self._handle_stop()

        # Other commands return BUSY if a macro is running
        if self._macro_runner.is_running:
            return bytes([RESP_BUSY])

        if cmd == CMD_PING:
            return self._handle_ping()
        elif cmd == CMD_GET_SENSOR:
            if len(params) < 1:
                return bytes([RESP_NACK])
            return self._handle_get_sensor(params[0])
        elif cmd == CMD_RUN_MACRO:
            if len(params) < 1:
                return bytes([RESP_NACK])
            return self._handle_run_macro(params[0])
        else:
            return bytes([RESP_NACK])

    def _handle_ping(self) -> bytes:
        """Handle PING command. Returns ACK."""
        return bytes([RESP_ACK])

    def _handle_get_sensor(self, sensor_id: int) -> bytes:
        """Handle GET_SENSOR command. Returns DATA with sensor value."""
        try:
            if sensor_id == SENSOR_PRESSURE:
                # Return raw ADC value as 2-byte big-endian
                raw = self._hw.pressure.read_raw()
                return bytes([RESP_DATA, 2, (raw >> 8) & 0xFF, raw & 0xFF])

            elif sensor_id == SENSOR_IGNITER_BATTERY:
                # Return millivolts as 2-byte big-endian
                voltage = self._hw.battery.read_igniter_voltage()
                mv = int(voltage * 1000)
                return bytes([RESP_DATA, 2, (mv >> 8) & 0xFF, mv & 0xFF])

            elif sensor_id == SENSOR_VALVE_BATTERY:
                # Return millivolts as 2-byte big-endian
                voltage = self._hw.battery.read_valve_voltage()
                mv = int(voltage * 1000)
                return bytes([RESP_DATA, 2, (mv >> 8) & 0xFF, mv & 0xFF])

            else:
                return bytes([RESP_NO_DATA])

        except Exception:
            return bytes([RESP_NO_DATA])

    def _handle_run_macro(self, macro_id: int) -> bytes:
        """Handle RUN_MACRO command. Returns ACK if valid, NACK if invalid."""
        success = self._macro_runner.start(macro_id)
        if success:
            return bytes([RESP_ACK])
        else:
            return bytes([RESP_NACK])

    def _handle_stop(self) -> bytes:
        """Handle STOP command. Always succeeds, stops any running macro."""
        self._macro_runner.stop()
        return bytes([RESP_ACK])

    def _send_response(self, response: bytes):
        """Send response over RS-485."""
        self._hw.rs485.send(response)
