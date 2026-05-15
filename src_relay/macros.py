"""
Macro definitions for Relay Box.

Macros are pre-defined relay patterns that can be triggered by command.
"""

import time
from hardware import RelayBoard, IgniterRelay

MACRO_COUNT = 11  # Macros 0-10

# =============================================================================
# Macro Step Definitions
# =============================================================================
# Each macro defines steps: [(relay_state, igniter_state, duration_ms), ...]
# - relay_state: byte value for PCF8574A (0xFF = all off, 0x00 = all on)
# - igniter_state: True = on, False = off
# - duration_ms: 0 = instant (complete immediately), >0 = timed step

MACRO_STEPS = {
    0: [(0xFF, False, 0)],       # All off - instant
    1: [(0x00, True, 0)],        # Fire all - until stopped
    2: [(0xFF, True, 0)],        # Igniter only - until stopped
    3: [(0x0F, False, 0)],       # Relays 1-4 - until stopped
    4: [(0xF0, False, 0)],       # Relays 5-8 - until stopped
    5: [(0x7F, False, 0)],       # Relay 1 only - until stopped
    6: [(0xBF, False, 0)],       # Relay 2 only - until stopped
    7: [(0xDF, False, 0)],       # Relay 3 only - until stopped
    8: [(0xEF, False, 0)],       # Relay 4 only - until stopped
    9: [(0x55, False, 0)],       # Odd relays - until stopped
    10: [(0xAA, False, 0)],      # Even relays - until stopped
}


# =============================================================================
# Macro Runner
# =============================================================================

class MacroRunner:
    """Manages macro execution state."""

    def __init__(self, relay_board: RelayBoard, igniter: IgniterRelay):
        self._relay_board = relay_board
        self._igniter = igniter
        self._current_macro = None  # Macro ID or None
        self._step = 0              # Current step within macro
        self._step_start_ms = 0     # When current step started

    @property
    def is_running(self) -> bool:
        """True if a macro is currently in progress."""
        return self._current_macro is not None

    def start(self, macro_id: int) -> bool:
        """Start a macro. Returns False if invalid macro ID."""
        if macro_id < 0 or macro_id >= MACRO_COUNT:
            return False
        self._current_macro = macro_id
        self._step = 0
        self._step_start_ms = time.ticks_ms()
        # Execute first step immediately
        self._execute_step()
        return True

    def stop(self):
        """Immediately stop any running macro and go to safe state."""
        self._current_macro = None
        self._relay_board.all_off()
        self._igniter.off()

    def tick(self):
        """Called each loop iteration. Advances macro state if needed."""
        if self._current_macro is None:
            return
        # Check if current step is complete, advance to next
        if self._is_step_complete():
            self._step += 1
            if self._step >= self._get_step_count():
                # Macro complete
                self._current_macro = None
            else:
                self._step_start_ms = time.ticks_ms()
                self._execute_step()

    def _execute_step(self):
        """Execute current step of current macro."""
        steps = MACRO_STEPS.get(self._current_macro, [])
        if self._step < len(steps):
            relay_state, igniter_state, _ = steps[self._step]
            self._relay_board.set_all(relay_state)
            if igniter_state:
                self._igniter.on()
            else:
                self._igniter.off()

    def _is_step_complete(self) -> bool:
        """Check if current step has completed."""
        steps = MACRO_STEPS.get(self._current_macro, [])
        if self._step >= len(steps):
            return True
        _, _, duration_ms = steps[self._step]
        if duration_ms == 0:
            # Instant step - stays active until stopped
            return False
        elapsed = time.ticks_diff(time.ticks_ms(), self._step_start_ms)
        return elapsed >= duration_ms

    def _get_step_count(self) -> int:
        """Get number of steps for current macro."""
        return len(MACRO_STEPS.get(self._current_macro, []))


def run_macro(macro_id: int, relay_board: RelayBoard, igniter: IgniterRelay) -> bool:
    """
    Execute macro 0-10. Returns True if valid macro, False if invalid.

    Relay board bit mapping (PCF8574A, active-low):
    - 0xFF = all relays OFF
    - 0x00 = all relays ON
    - Bit 0 = Relay 8, Bit 7 = Relay 1

    Placeholder implementations with various relay patterns.
    """
    if macro_id < 0 or macro_id >= MACRO_COUNT:
        return False

    if macro_id == 0:
        # Macro 0: All off (safe state)
        relay_board.all_off()
        igniter.off()

    elif macro_id == 1:
        # Macro 1: Fire all (all NC open + all NO open + igniter)
        # All 8 relays ON plus igniter
        relay_board.set_all(0x00)  # All ON (active-low)
        igniter.on()

    elif macro_id == 2:
        # Macro 2: Igniter only
        relay_board.all_off()
        igniter.on()

    elif macro_id == 3:
        # Macro 3: Relays 1-4 only (no igniter)
        # Bits 7-4 = 0 (ON), Bits 3-0 = 1 (OFF)
        relay_board.set_all(0x0F)
        igniter.off()

    elif macro_id == 4:
        # Macro 4: Relays 5-8 only (no igniter)
        # Bits 7-4 = 1 (OFF), Bits 3-0 = 0 (ON)
        relay_board.set_all(0xF0)
        igniter.off()

    elif macro_id == 5:
        # Macro 5: Relay 1 only
        relay_board.set_all(0x7F)  # Bit 7 = 0 (ON)
        igniter.off()

    elif macro_id == 6:
        # Macro 6: Relay 2 only
        relay_board.set_all(0xBF)  # Bit 6 = 0 (ON)
        igniter.off()

    elif macro_id == 7:
        # Macro 7: Relay 3 only
        relay_board.set_all(0xDF)  # Bit 5 = 0 (ON)
        igniter.off()

    elif macro_id == 8:
        # Macro 8: Relay 4 only
        relay_board.set_all(0xEF)  # Bit 4 = 0 (ON)
        igniter.off()

    elif macro_id == 9:
        # Macro 9: Odd relays (1, 3, 5, 7)
        relay_board.set_all(0x55)  # 0b01010101
        igniter.off()

    elif macro_id == 10:
        # Macro 10: Even relays (2, 4, 6, 8)
        relay_board.set_all(0xAA)  # 0b10101010
        igniter.off()

    return True
