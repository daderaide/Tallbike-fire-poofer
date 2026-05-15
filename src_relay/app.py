"""
Main application for Relay Box ESP32-S3.

This module initializes hardware and runs the main command loop.
"""

from hardware import Hardware
from comms import CommandHandler


class RelayBoxApp:
    """Main Relay Box application class."""

    def __init__(self):
        """Initialize the application and hardware."""
        self._hardware = Hardware()
        self._command_handler = CommandHandler(self._hardware)

        # Safety: ensure all relays off at startup
        self._hardware.relay_board.all_off()
        self._hardware.igniter.off()

    def run(self):
        """Run the main application loop."""
        # Enter main command loop (runs forever)
        self._command_handler.run()
