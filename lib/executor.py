# executor.py — Macro execution engine (relay box only)
# Looping step sequencer with igniter cooldown and finishing step
# No direct import of poof — functions passed in to avoid circular deps

import time
from comms import modbus

# NC valves are 1-4, NO valves are 5-8
NC_VALVES = {1, 2, 3, 4}

# All relays off (active low)
ALL_OFF = 0xFF

# Igniter limits
IGN_MAX_MS = 1000        # hardware hard cap
IGN_COOLDOWN_RATIO = 1.0 # off-time >= on-time (50% max duty)

# Executor states
IDLE = 0
WAITING_PRESSURE = 1
RUNNING_STEP = 2
DELAY_AFTER = 3
IGN_COOLDOWN = 4
FINISHING = 5

class Executor:
    def __init__(self, set_relays_fn, set_igniter_fn):
        self._set_relays = set_relays_fn
        self._set_igniter = set_igniter_fn
        self.macro = None
        self.step_idx = 0
        self.state = IDLE
        self._step_start_ms = 0
        self._delay_start_ms = 0
        self._cooldown_start_ms = 0
        self._cooldown_dur_ms = 0

        # Igniter state
        self._ign_active = False
        self._ign_started = False
        self._ign_start_ms = 0
        self._ign_dur_ms = 0
        self._ign_off_ms = 0       # when igniter last turned off
        self._ign_last_on_ms = 0   # how long it was on last time

        # Button state
        self._btn_pressed = False
        self._btn_released = False  # edge-triggered flag
        self._first_cycle = True    # minimum one full cycle on press

        # Valve tracking for igniter skip logic
        self._prev_nc_valves = set()
        self._prev_delay_after = -1  # -1 = no previous step

        # Meltdown warning flag
        self.ign_cooldown_warning = False

    def start(self, macro):
        """Start executing a macro from dict."""
        self.macro = macro
        self.step_idx = 0
        self._first_cycle = True
        self._btn_released = False
        self._prev_nc_valves = set()
        self._prev_delay_after = -1
        self.ign_cooldown_warning = False
        # print('EXEC: start, {} steps, finishing={}'.format(
        #     len(macro.get('steps', [])), macro.get('finishing_step') is not None))
        # for i, s in enumerate(macro.get('steps', [])):
        #     print('EXEC: step[{}] dur={} delay={} psi={} ign_dur={} ign_off={} valves={}'.format(
        #         i, s.get('duration'), s.get('delay_after'), s.get('pressure'),
        #         s.get('ign_dur'), s.get('ign_offset'), s.get('valves')))
        self._begin_step()

    def stop(self):
        """Stop execution, all off."""
        self.macro = None
        self.state = IDLE
        self.step_idx = 0
        self._set_relays(ALL_OFF)
        self._set_igniter(0)
        self._ign_active = False
        self._prev_nc_valves = set()
        self._prev_delay_after = -1
        modbus.set_hreg(0, 1)  # back to armed
        modbus.set_hreg(9, 0)  # no active macro

    def set_button_state(self, pressed):
        """Called when fire register changes."""
        if not pressed and self._btn_pressed:
            self._btn_released = True
        self._btn_pressed = pressed

    @property
    def running(self):
        return self.state != IDLE

    def update(self):
        """Call every loop iteration."""
        if self.state == IDLE:
            return

        now = time.ticks_ms()

        # Hardware hard cap on igniter
        if self._ign_active:
            elapsed = time.ticks_diff(now, self._ign_start_ms)
            if elapsed >= IGN_MAX_MS:
                self._igniter_off(now)

        # Check for button release — always stop if released, even during first cycle
        # when waiting for pressure (no point waiting with no button held)
        if self._btn_released:
            if self.state == FINISHING:
                pass  # already finishing
            elif self.state == WAITING_PRESSURE:
                # No point waiting for pressure with no button held
                self._start_finishing(now)
                return
            elif not self._first_cycle:
                self._start_finishing(now)
                return

        if self.state == WAITING_PRESSURE:
            step = self._current_step()
            threshold = step.get('pressure', 0)
            if threshold == 0:
                self._fire_step(step, now)
            else:
                pressure = modbus.get_hreg(2)
                if pressure >= threshold:
                    self._fire_step(step, now)

        elif self.state == RUNNING_STEP:
            step = self._current_step()
            self._update_running(step, now)

        elif self.state == DELAY_AFTER:
            step = self._current_step()
            delay = step.get('delay_after', 0)
            if time.ticks_diff(now, self._delay_start_ms) >= delay:
                self._advance_step(now)

        elif self.state == IGN_COOLDOWN:
            elapsed = time.ticks_diff(now, self._cooldown_start_ms)
            if elapsed >= self._cooldown_dur_ms:
                self.ign_cooldown_warning = False
                modbus.set_hreg(8, 0)  # clear error
                self._begin_step()

        elif self.state == FINISHING:
            step = self.macro.get('finishing_step')
            if step:
                self._update_running(step, now)

    def _current_step(self):
        return self.macro['steps'][self.step_idx]

    def _begin_step(self):
        """Start processing a step (pressure check then fire)."""
        if self.step_idx >= len(self.macro['steps']):
            # End of sequence
            if self._first_cycle:
                self._first_cycle = False
            # Check if button was released during this cycle
            if self._btn_released:
                # print('EXEC: end of cycle, btn released -> finishing')
                self._start_finishing(time.ticks_ms())
                return
            # Loop back
            # print('EXEC: end of cycle, looping')
            self.step_idx = 0

        step = self._current_step()
        modbus.set_hreg(0, 2)  # system_state = firing
        modbus.set_hreg(9, self.step_idx + 1)

        threshold = step.get('pressure', 0)
        # print('EXEC: begin step[{}] pressure={}'.format(self.step_idx, threshold))
        if threshold > 0:
            self.state = WAITING_PRESSURE
        else:
            self._fire_step(step, time.ticks_ms())

    def _needs_igniter(self, step):
        """Check if this step needs the igniter to fire."""
        nc_in_step = set()
        for v in step.get('valves', []):
            if v in NC_VALVES:
                nc_in_step.add(v)
        if not nc_in_step:
            return False, nc_in_step

        # Skip igniter if same NC valves as previous step with zero delay
        if self._prev_delay_after == 0 and nc_in_step == self._prev_nc_valves:
            return False, nc_in_step

        return True, nc_in_step

    def _check_cooldown(self, now):
        """Check if igniter cooldown has elapsed. Returns True if ready."""
        if self._ign_last_on_ms == 0:
            return True  # never fired yet
        off_elapsed = time.ticks_diff(now, self._ign_off_ms)
        required = int(self._ign_last_on_ms * IGN_COOLDOWN_RATIO)
        return off_elapsed >= required

    def _fire_step(self, step, now):
        """Activate valves and schedule igniter."""
        needs_ign, nc_in_step = self._needs_igniter(step)

        # If igniter needed, check cooldown
        if needs_ign and not self._check_cooldown(now):
            self.state = IGN_COOLDOWN
            self.ign_cooldown_warning = True
            modbus.set_hreg(8, 6)  # error code for igniter cooldown
            self._cooldown_start_ms = now
            required = int(self._ign_last_on_ms * IGN_COOLDOWN_RATIO)
            off_elapsed = time.ticks_diff(now, self._ign_off_ms)
            self._cooldown_dur_ms = required - off_elapsed
            return

        self.state = RUNNING_STEP
        self._step_start_ms = now
        self._ign_active = False
        self._ign_started = False
        self._ign_dur_ms = 0

        # Open valves
        bitmask = ALL_OFF
        for v in step.get('valves', []):
            bit = v - 1
            bitmask &= ~(1 << bit)
        self._set_relays(bitmask)

        # Schedule igniter
        if needs_ign:
            ign_offset = step.get('ign_offset', 0)
            self._ign_dur_ms = min(step.get('ign_dur', 0), IGN_MAX_MS)
            self._ign_start_ms = now + ign_offset

            if ign_offset <= 0:
                self._set_igniter(1)
                self._ign_active = True
                self._ign_started = True
                self._ign_start_ms = now

        # Track NC valves for next step's igniter skip logic
        self._prev_nc_valves = nc_in_step

    def _update_running(self, step, now):
        """Manage valve and igniter timing each tick."""
        # Start igniter if offset time has come
        if not self._ign_started and self._ign_dur_ms > 0:
            if time.ticks_diff(now, self._ign_start_ms) >= 0:
                self._set_igniter(1)
                self._ign_active = True
                self._ign_started = True
                self._ign_start_ms = now  # reset for duration tracking

        # Check igniter duration
        if self._ign_active:
            elapsed = time.ticks_diff(now, self._ign_start_ms)
            if elapsed >= self._ign_dur_ms:
                self._igniter_off(now)

        # Check step duration
        duration = step.get('duration', 0)
        elapsed = time.ticks_diff(now, self._step_start_ms)
        if elapsed >= duration:
            # Step complete — kill igniter regardless
            if self._ign_active:
                self._igniter_off(now)

            if self.state == FINISHING:
                self._set_relays(ALL_OFF)
                self.stop()
                return

            # Track delay_after for igniter skip logic
            self._prev_delay_after = step.get('delay_after', 0)

            delay = step.get('delay_after', 0)
            if delay > 0:
                # Has a gap — close valves, wait
                self._set_relays(ALL_OFF)
                self.state = DELAY_AFTER
                self._delay_start_ms = time.ticks_ms()
            else:
                # Zero delay — skip ALL_OFF, let next _fire_step
                # set the bitmask directly (avoids loop stutter)
                self._advance_step(now)

    def _igniter_off(self, now):
        """Turn off igniter and record timing for cooldown."""
        self._set_igniter(0)
        on_time = time.ticks_diff(now, self._ign_start_ms)
        self._ign_last_on_ms = on_time
        self._ign_off_ms = now
        self._ign_active = False

    def _start_finishing(self, now):
        """Button released — fire finishing step or stop."""
        # Close current valves immediately
        self._set_relays(ALL_OFF)
        if self._ign_active:
            self._igniter_off(now)

        finishing = self.macro.get('finishing_step')
        if finishing:
            self.state = FINISHING
            self._prev_delay_after = -1  # force igniter on finishing step
            self._fire_step(finishing, now)
            self.state = FINISHING  # _fire_step sets RUNNING_STEP, override
        else:
            self.stop()

    def _advance_step(self, now):
        """Move to next step or loop."""
        self.step_idx += 1
        self._begin_step()