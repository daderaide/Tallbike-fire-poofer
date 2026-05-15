"""
MicroPython entry point for Relay Box.

This file is automatically executed by MicroPython on boot.
"""

from app import RelayBoxApp

app = RelayBoxApp()
app.run()
