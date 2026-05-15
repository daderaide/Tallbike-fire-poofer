"""
RS-485 client for sending commands to Relay Box.

This module implements the client side of the command/response protocol.
"""

from hardware import RS485

# =============================================================================
# Protocol Constants (must match src_relay/comms.py)
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
# Relay Box Client
# =============================================================================

class RelayBoxClient:
    """Client for communicating with the Relay Box over RS-485."""

    def __init__(self, rs485: RS485):
        self._rs485 = rs485

    def ping(self) -> bool:
        """
        Send PING command.

        Returns True if ACK received, False otherwise.
        """
        response = self._rs485.send_and_receive(bytes([CMD_PING]))
        if response is None or len(response) < 1:
            return False
        return response[0] == RESP_ACK

    def get_pressure(self) -> int | None:
        """
        Get pressure sensor raw ADC value.

        Returns raw 12-bit ADC value (0-4095) or None on failure.
        """
        response = self._rs485.send_and_receive(bytes([CMD_GET_SENSOR, SENSOR_PRESSURE]))
        return self._parse_data_response(response)

    def get_igniter_battery_mv(self) -> int | None:
        """
        Get igniter battery voltage in millivolts.

        Returns voltage in mV or None on failure.
        """
        response = self._rs485.send_and_receive(bytes([CMD_GET_SENSOR, SENSOR_IGNITER_BATTERY]))
        return self._parse_data_response(response)

    def get_valve_battery_mv(self) -> int | None:
        """
        Get valve battery voltage in millivolts.

        Returns voltage in mV or None on failure.
        """
        response = self._rs485.send_and_receive(bytes([CMD_GET_SENSOR, SENSOR_VALVE_BATTERY]))
        return self._parse_data_response(response)

    def run_macro(self, macro_id: int) -> bool:
        """
        Start a macro on the Relay Box.

        Args:
            macro_id: Macro ID (1-255)

        Returns True if ACK received, False otherwise.
        """
        response = self._rs485.send_and_receive(bytes([CMD_RUN_MACRO, macro_id]))
        if response is None or len(response) < 1:
            return False
        return response[0] == RESP_ACK

    def stop(self) -> bool:
        """
        Send STOP command to halt any running macro.

        Returns True if ACK received, False otherwise.
        """
        response = self._rs485.send_and_receive(bytes([CMD_STOP]))
        if response is None or len(response) < 1:
            return False
        return response[0] == RESP_ACK

    def _parse_data_response(self, response: bytes | None) -> int | None:
        """
        Parse a DATA response containing a 2-byte big-endian value.

        Expected format: [RESP_DATA, length, high_byte, low_byte]
        """
        if response is None or len(response) < 4:
            return None
        if response[0] != RESP_DATA:
            return None
        if response[1] != 2:
            return None
        # Parse 2-byte big-endian value
        value = (response[2] << 8) | response[3]
        return value
