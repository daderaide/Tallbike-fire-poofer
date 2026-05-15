"""
Button and rotary encoder input handling with debouncing.
"""

try:
    from machine import Pin
    import time
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    Pin = None
    time = None

from hardware import PIN_MAIN_BTN, PIN_AUX_BTN, PIN_ENC_CLK, PIN_ENC_DT, PIN_ENC_SW


class Button:
    """Debounced button with configurable pull-up."""

    DEBOUNCE_MS = 20

    def __init__(self, pin_num: int, pull_up: bool = True):
        self._pin_num = pin_num
        self._last_state = False
        self._stable_state = False
        self._last_change_ms = 0

        if MICROPYTHON:
            if pull_up:
                self._pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
            else:
                self._pin = Pin(pin_num, Pin.IN)
        else:
            self._pin = None

    @property
    def is_pressed(self) -> bool:
        """Returns current debounced state (True = pressed)."""
        return self._stable_state

    def update(self):
        """Call each loop iteration for debouncing."""
        if not MICROPYTHON:
            return

        # Buttons with pull-up read LOW when pressed
        current_raw = self._pin.value() == 0

        now = time.ticks_ms()

        if current_raw != self._last_state:
            self._last_state = current_raw
            self._last_change_ms = now
        elif time.ticks_diff(now, self._last_change_ms) > self.DEBOUNCE_MS:
            self._stable_state = current_raw


class RotaryEncoder:
    """Rotary encoder with push button."""

    DEBOUNCE_MS = 5

    def __init__(self, clk_pin: int, dt_pin: int, sw_pin: int):
        self._position = 0
        self._last_clk = False
        self._button = Button(sw_pin, pull_up=True)

        if MICROPYTHON:
            # CLK and DT have external pull-ups
            self._clk = Pin(clk_pin, Pin.IN)
            self._dt = Pin(dt_pin, Pin.IN)
            self._last_clk = self._clk.value() == 1
        else:
            self._clk = None
            self._dt = None

    @property
    def position(self) -> int:
        """Get accumulated position."""
        return self._position

    @position.setter
    def position(self, value: int):
        """Set position (useful for resetting)."""
        self._position = value

    @property
    def button_pressed(self) -> bool:
        """Get encoder button state."""
        return self._button.is_pressed

    def update(self):
        """Poll encoder state, update position."""
        if not MICROPYTHON:
            return

        # Update button
        self._button.update()

        # Read encoder
        clk = self._clk.value() == 1
        dt = self._dt.value() == 1

        # Detect falling edge on CLK
        if self._last_clk and not clk:
            # Direction determined by DT state
            if dt:
                self._position += 1
            else:
                self._position -= 1

        self._last_clk = clk


class InputManager:
    """Manages all input devices."""

    def __init__(self):
        self.main_button = Button(PIN_MAIN_BTN, pull_up=True)
        self.aux_button = Button(PIN_AUX_BTN, pull_up=True)
        self.encoder = RotaryEncoder(PIN_ENC_CLK, PIN_ENC_DT, PIN_ENC_SW)

    def update(self):
        """Update all inputs (call each loop iteration)."""
        self.main_button.update()
        self.aux_button.update()
        self.encoder.update()
