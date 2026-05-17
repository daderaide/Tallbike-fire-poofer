# executor.py — Macro execution engine (relay box only)
# Walks through macro steps, controls valves and igniter with timing
# No direct import of poof — functions passed in to avoid circular deps

import time
import json
from comms import modbus

# NC valves are 1-4, NO valves are 5-8
NC_VALVES = {1, 2, 3, 4}

# All relays off (active low)
ALL_OFF = 0xFF

# Executor states
IDLE = 0
WAITING_PRESSURE = 1
WAITING_TRIGGER = 2
RUNNING_STEP = 3
DELAY_AFTER = 4

class Executor:
    def __init__(self, set_relays_fn, set_igniter_fn):
        self._set_relays = set_relays_fn
        self._set_igniter = set_igniter_fn
        self.macro = None
        self.step_idx = 0
        self.state = IDLE
        self._step_start_ms = 0
        self._delay_start_ms = 0
        self._ign_start_ms = 0
        self._ign_active = False
        self._ign_dur_ms = 0
        self._ign_started = False
        self._valve_timers = []
        self._btn_pressed = False
        self._btn_was_pressed = False

    def start(self, macro):
        """Start executing a macro from dict."""
        self.macro = macro
        self.step_idx = 0
        self._btn_was_pressed = self._btn_pressed
        self._begin_step()

    def stop(self):
        """Stop execution, all off."""
        self.macro = None
        self.state = IDLE
        self.step_idx = 0
        self._set_relays(ALL_OFF)
        self._set_igniter(0)
        self._ign_active = False
        self._valve_timers = []
        modbus.set_hreg(0, 1)  # back to armed
        modbus.set_hreg(9, 0)  # no active macro

    def set_button_state(self, pressed):
        """Called when fire register changes."""
        self._btn_was_pressed = self._btn_pressed
        self._btn_pressed = pressed

    @property
    def button_released(self):
        return self._btn_was_pressed and not self._btn_pressed

    @property
    def running(self):
        return self.state != IDLE

    def update(self):
        """Call every loop iteration."""
        if self.state == IDLE:
            return

        now = time.ticks_ms()
        step = self.macro['steps'][self.step_idx]

        if self.state == WAITING_PRESSURE:
            threshold = step.get('pressure', 0)
            if threshold == 0:
                self._enter_waiting_trigger(step)
            else:
                pressure = modbus.get_hreg(2)
                if pressure >= threshold:
                    self._enter_waiting_trigger(step)

        elif self.state == WAITING_TRIGGER:
            trigger = step.get('trigger', 'press')
            if trigger == 'press':
                if self._btn_pressed:
                    self._fire_step(step, now)
            elif trigger == 'release':
                if self.button_released:
                    self._fire_step(step, now)
            elif trigger == 'immediate':
                self._fire_step(step, now)

        elif self.state == RUNNING_STEP:
            self._update_step(step, now)

        elif self.state == DELAY_AFTER:
            delay = step.get('delay_after', 0)
            if time.ticks_diff(now, self._delay_start_ms) >= delay:
                self._advance_step()

    def _begin_step(self):
        """Start processing a step."""
        if self.step_idx >= len(self.macro['steps']):
            self.stop()
            return
        step = self.macro['steps'][self.step_idx]
        modbus.set_hreg(0, 2)  # system_state = firing
        modbus.set_hreg(9, self.step_idx + 1)

        threshold = step.get('pressure', 0)
        if threshold > 0:
            self.state = WAITING_PRESSURE
        else:
            self._enter_waiting_trigger(step)

    def _enter_waiting_trigger(self, step):
        """Pressure met, wait for trigger."""
        trigger = step.get('trigger', 'press')
        if trigger == 'immediate':
            self._fire_step(step, time.ticks_ms())
        elif trigger == 'press' and self._btn_pressed:
            self._fire_step(step, time.ticks_ms())
        elif trigger == 'release' and self.button_released:
            self._fire_step(step, time.ticks_ms())
        else:
            self.state = WAITING_TRIGGER

    def _fire_step(self, step, now):
        """Activate valves and schedule igniter."""
        self.state = RUNNING_STEP
        self._step_start_ms = now
        self._valve_timers = []
        self._ign_active = False
        self._ign_started = False

        bitmask = ALL_OFF
        has_nc = False

        for v in step.get('valves', []):
            valve_num = v['valve']
            dur = v.get('duration', 0)
            bit = valve_num - 1
            bitmask &= ~(1 << bit)

            if dur == 'held':
                dur_ms = -1
            else:
                dur_ms = dur

            self._valve_timers.append((valve_num, now, dur_ms))

            if valve_num in NC_VALVES:
                has_nc = True

        self._set_relays(bitmask)

        if has_nc:
            ign_offset = step.get('ign_offset', 0)
            ign_dur = step.get('ign_dur', 'held')

            if ign_dur == 'held':
                self._ign_dur_ms = -1
            else:
                self._ign_dur_ms = ign_dur

            self._ign_start_ms = now + ign_offset
            if ign_offset <= 0:
                self._set_igniter(1)
                self._ign_active = True
                self._ign_started = True

    def _update_step(self, step, now):
        """Manage valve and igniter timing each tick."""

        # Start igniter if positive offset time has come
        if not self._ign_started and hasattr(self, '_ign_start_ms'):
            if time.ticks_diff(now, self._ign_start_ms) >= 0:
                self._set_igniter(1)
                self._ign_active = True
                self._ign_started = True

        # Check igniter duration
        if self._ign_active:
            if self._ign_dur_ms == -1:
                pass  # held — stays on while NC valves are open
            else:
                ign_ref = max(self._ign_start_ms, self._step_start_ms)
                elapsed = time.ticks_diff(now, ign_ref)
                if elapsed >= self._ign_dur_ms:
                    self._set_igniter(0)
                    self._ign_active = False

        # Check each valve timer
        all_done = True
        any_nc_open = False
        new_bitmask = ALL_OFF

        for i, (valve_num, start_ms, dur_ms) in enumerate(self._valve_timers):
            if dur_ms == -1:
                if self._btn_pressed:
                    bit = valve_num - 1
                    new_bitmask &= ~(1 << bit)
                    all_done = False
                    if valve_num in NC_VALVES:
                        any_nc_open = True
            else:
                elapsed = time.ticks_diff(now, start_ms)
                if elapsed < dur_ms:
                    bit = valve_num - 1
                    new_bitmask &= ~(1 << bit)
                    all_done = False
                    if valve_num in NC_VALVES:
                        any_nc_open = True

        self._set_relays(new_bitmask)

        # If igniter is "held" and no NC valves are open, turn it off
        if self._ign_active and self._ign_dur_ms == -1 and not any_nc_open:
            self._set_igniter(0)
            self._ign_active = False

        if all_done:
            self._set_igniter(0)
            self._ign_active = False
            delay = step.get('delay_after', 0)
            if delay > 0:
                self.state = DELAY_AFTER
                self._delay_start_ms = time.ticks_ms()
            else:
                self._advance_step()

    def _advance_step(self):
        """Move to next step or finish macro."""
        self.step_idx += 1
        if self.step_idx >= len(self.macro['steps']):
            self.stop()
        else:
            self._begin_step()