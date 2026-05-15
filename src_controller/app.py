"""
Main application class for the Control Box.

This is the master device that sends commands to the Relay Box over RS-485.
"""

try:
    import time
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    time = None

from hardware import Hardware
from sensors import BatteryMonitor
from comms import RelayBoxClient
from inputs import InputManager
from leds import LEDManager
from display import DisplayManager


class App:
    """Main application for the Control Box."""

    # Timing constants
    BOOT_DELAY_MS = 3000        # Wait for RS-485 stabilization
    LOOP_INTERVAL_MS = 50       # 20 Hz main loop
    SENSOR_POLL_MS = 500        # Poll remote sensors every 500ms
    PING_INTERVAL_MS = 2000     # Ping relay box every 2s

    def __init__(self):
        # Show boot delay
        print("Control Box starting...")
        print(f"Waiting {self.BOOT_DELAY_MS}ms for RS-485 stabilization...")

        if MICROPYTHON:
            time.sleep_ms(self.BOOT_DELAY_MS)

        # Initialize hardware
        self._hw = Hardware()

        # Enable RS-485 drive mode after boot delay
        self._hw.rs485.enable_drive()
        print("RS-485 drive enabled")

        # Initialize subsystems
        self._inputs = InputManager()
        self._leds = LEDManager()
        self._display = DisplayManager(self._hw.i2c)
        self._relay_client = RelayBoxClient(self._hw.rs485)
        self._battery = BatteryMonitor(self._hw.battery_adc)

        # Set random LED colors on startup
        self._leds.set_random_colors()
        print("LEDs initialized with random colors")

        # Show startup message
        self._display.show_startup_message()

        # Timing state
        self._last_sensor_poll = 0
        self._last_ping = 0
        self._start_time = 0
        if MICROPYTHON:
            self._start_time = time.ticks_ms()

        # Connection state
        self._relay_connected = False

        print("Control Box ready")

    def run(self):
        """Main loop - runs forever."""
        while True:
            self._tick()
            if MICROPYTHON:
                time.sleep_ms(self.LOOP_INTERVAL_MS)

    def _tick(self):
        """Single iteration of the main loop."""
        now = 0
        if MICROPYTHON:
            now = time.ticks_ms()

        # Update inputs
        self._inputs.update()

        # Update uptime display
        uptime = 0
        if MICROPYTHON:
            uptime = time.ticks_diff(now, self._start_time)
        self._display.update_uptime(uptime)

        # Read local battery
        voltage = self._battery.read_voltage()
        self._display.update_control_battery(voltage)

        # Periodic ping to check connection
        if MICROPYTHON:
            if time.ticks_diff(now, self._last_ping) > self.PING_INTERVAL_MS:
                self._last_ping = now
                self._relay_connected = self._relay_client.ping()
                self._display.update_connection_status(self._relay_connected)

        # Poll remote sensors periodically
        if MICROPYTHON:
            if time.ticks_diff(now, self._last_sensor_poll) > self.SENSOR_POLL_MS:
                self._last_sensor_poll = now
                self._poll_remote_sensors()

        # Update display with input states
        self._display.update_inputs(
            self._inputs.main_button.is_pressed,
            self._inputs.aux_button.is_pressed,
            self._inputs.encoder.position
        )

        # Handle main button (fire while held)
        if self._inputs.main_button.is_pressed:
            self._relay_client.run_macro(1)  # Fire all
        else:
            # Only send stop if we were previously firing
            # (Could optimize to not spam STOP commands)
            self._relay_client.stop()

    def _poll_remote_sensors(self):
        """Poll pressure and battery readings from Relay Box."""
        # Get pressure
        pressure_raw = self._relay_client.get_pressure()
        if pressure_raw is not None:
            # Convert raw ADC to PSI
            # Sensor: 0.5V at 0 PSI, 4.5V at 500 PSI
            # ADS1015: 12-bit, 4.096V range, so 2048 counts = 4.096V
            voltage = (pressure_raw / 2048.0) * 4.096
            psi = ((voltage - 0.5) / 4.0) * 500.0
            psi = max(0.0, min(500.0, psi))
            self._display.update_pressure(psi)

        # Get remote battery voltages
        igniter_mv = self._relay_client.get_igniter_battery_mv()
        valve_mv = self._relay_client.get_valve_battery_mv()

        if igniter_mv is not None or valve_mv is not None:
            self._display.update_remote_batteries(
                igniter_mv if igniter_mv is not None else 0,
                valve_mv if valve_mv is not None else 0
            )
