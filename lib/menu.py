# menu.py — Screen-stack menu system (control box only)
# Encoder scrolls cursor, click selects, aux goes back

from display import lcd

# --- Color Presets ---

COLORS = [
    ('Red', (255, 0, 0)),
    ('Orange', (255, 80, 0)),
    ('Yellow', (255, 200, 0)),
    ('Green', (0, 255, 0)),
    ('Cyan', (0, 255, 200)),
    ('Blue', (0, 0, 255)),
    ('Purple', (128, 0, 255)),
    ('Pink', (255, 0, 128)),
    ('White', (255, 255, 255)),
    ('Rainbow', 'rainbow'),
]

# --- Base Screen ---

class Screen:
    def __init__(self):
        self.cursor = 0
        self.scroll_offset = 0
        self._dirty = [True, True, True, True]

    def items(self):
        return []

    def on_click(self, index):
        return None

    def mark_dirty(self, line=None):
        if line is None:
            for i in range(4):
                self._dirty[i] = True
        else:
            self._dirty[line] = True

    def on_scroll(self, delta):
        count = len(self.items())
        if count == 0:
            return
        old_cursor = self.cursor
        old_offset = self.scroll_offset

        if delta > 0:
            self.cursor = min(self.cursor + 1, count - 1)
        elif delta < 0:
            self.cursor = max(self.cursor - 1, 0)

        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + 4:
            self.scroll_offset = self.cursor - 3

        if self.cursor != old_cursor or self.scroll_offset != old_offset:
            self.mark_dirty()

    def draw(self):
        rows = self.items()
        for i in range(4):
            if not self._dirty[i]:
                continue
            idx = self.scroll_offset + i
            lcd.set_cursor(0, i)
            if idx < len(rows):
                prefix = '>' if idx == self.cursor else ' '
                line = prefix + rows[idx]
                lcd.print('{:<20}'.format(line[:20]))
            else:
                lcd.print('{:<20}'.format(''))
            self._dirty[i] = False


# --- Value Edit Screen ---

class ValueEditScreen(Screen):
    def __init__(self, label, value, min_val, max_val, step, suffix='', on_save=None):
        super().__init__()
        self.label = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.suffix = suffix
        self.on_save = on_save

    def items(self):
        return [
            self.label,
            '',
            '{}{}'.format(self.value, self.suffix),
            'Click to confirm'
        ]

    def on_scroll(self, delta):
        old = self.value
        if delta > 0:
            self.value = min(self.value + self.step, self.max_val)
        elif delta < 0:
            self.value = max(self.value - self.step, self.min_val)
        if self.value != old:
            self.mark_dirty()

    def on_click(self, index):
        if self.on_save:
            self.on_save(self.value)
        return 'pop'


# --- Choice Screen ---

class ChoiceScreen(Screen):
    def __init__(self, label, options, current, on_save=None):
        super().__init__()
        self.label = label
        self.options = options
        self.on_save = on_save
        self.cursor = current if current < len(options) else 0

    def items(self):
        rows = [self.label]
        for i, opt in enumerate(self.options):
            marker = '*' if i == self.cursor else ' '
            rows.append('{}{}'.format(marker, opt))
        return rows

    def on_click(self, index):
        if index > 0:
            selection = index - 1
            if self.on_save:
                self.on_save(selection)
            return 'pop'
        return None


# --- Name Edit Screen ---

class NameEditScreen(Screen):
    def __init__(self, name, on_save=None):
        super().__init__()
        self._chars = list(name)
        self._pos = 0
        self._editing = False
        self.on_save = on_save
        self._charset = list(' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')

    def items(self):
        name = ''.join(self._chars)
        if self._editing:
            cursor_line = ' ' * self._pos + '^'
            return [
                'Edit Name',
                name[:19],
                cursor_line[:19],
                'Scroll=char Click=ok'
            ]
        else:
            return [
                'Edit Name',
                name[:19],
                'Pos:{}'.format(self._pos + 1),
                'Click=edit Aux=done'
            ]

    def on_scroll(self, delta):
        if self._editing:
            c = self._chars[self._pos]
            idx = self._charset.index(c) if c in self._charset else 0
            idx = (idx + delta) % len(self._charset)
            self._chars[self._pos] = self._charset[idx]
        else:
            self._pos = max(0, min(self._pos + delta, len(self._chars) - 1))
        self.mark_dirty()

    def on_click(self, index):
        if self._editing:
            self._editing = False
        else:
            self._editing = True
        self.mark_dirty()
        return None

    def on_back(self):
        if self._editing:
            self._editing = False
            self.mark_dirty()
            return False
        if self.on_save:
            self.on_save(''.join(self._chars).strip())
        return True


# --- Home Screen ---

class HomeScreen(Screen):
    def __init__(self):
        super().__init__()
        self.state = 0
        self.error = 0
        self.pressure = 0
        self.batt_ign = 0
        self.batt_valve = 0
        self.batt_ctrl = 0
        self.connected = False
        self.aux_macro_name = '(none)'
        self.aux_macro_color = None

    def items(self):
        from display import STATE_NAMES, ERROR_NAMES
        if not self.connected:
            return ['THE FUPA', 'No relay box', 'Macro: ' + self.aux_macro_name, 'Settings']

        state_name = STATE_NAMES.get(self.state, '???')
        line1 = '{} | {}psi'.format(state_name, self.pressure)

        if self.error > 0:
            line2 = ERROR_NAMES.get(self.error, '???')
        else:
            # Show lowest battery percentage as quick glance
            from battery import percent_1s, percent_3s
            pct_ctrl = percent_1s(self.batt_ctrl)
            pct_ign = percent_1s(self.batt_ign)
            pct_valve = percent_3s(self.batt_valve)
            min_pct = min(p for p in [pct_ctrl, pct_ign, pct_valve] if p > 0) if any([pct_ctrl, pct_ign, pct_valve]) else 0
            line2 = 'Batt: {}%'.format(min_pct)

        return [line1, line2, 'Macro: ' + self.aux_macro_name, 'Settings']

    def update_status(self, state, error, pressure, batt_ign, batt_valve, batt_ctrl):
        changed = (state != self.state or error != self.error or
                   pressure != self.pressure or batt_ign != self.batt_ign or
                   batt_valve != self.batt_valve or batt_ctrl != self.batt_ctrl)
        self.state = state
        self.error = error
        self.pressure = pressure
        self.batt_ign = batt_ign
        self.batt_valve = batt_valve
        self.batt_ctrl = batt_ctrl
        self.connected = True
        if changed:
            self.mark_dirty()

    def set_disconnected(self):
        if self.connected:
            self.connected = False
            self.mark_dirty()

    def on_click(self, index):
        items = self.items()
        if items[index].startswith('Macro:'):
            return MacroListScreen(self)
        if items[index] == 'Settings':
            return SettingsScreen(self)
        if items[index].startswith('Batt:'):
            return BatteryScreen(self)
        return None


# --- Macro List Screen ---

class MacroListScreen(Screen):
    def __init__(self, home):
        super().__init__()
        self.home = home
        self._refresh()

    def _refresh(self):
        from macro_store import list_macros
        self._macros = list_macros()
        self.mark_dirty()

    def items(self):
        rows = ['(none)', 'New Macro']
        for name in self._macros:
            rows.append(name)
        return rows

    def on_click(self, index):
        if index == 0:
            # Unassign aux macro
            self.home.aux_macro_name = '(none)'
            self.home.aux_macro_color = None
            return 'home'
        if index == 1:
            return self._create_new()
        name = self._macros[index - 2]
        if name == 'main_poof':
            from macro_store import load
            macro = load(name)
            return MacroEditScreen(name, macro, self)
        else:
            return AssignScreen(name, self.home, self)

    def _create_new(self):
        from macro_store import save
        num = 1
        while 'Macro {}'.format(num) in [self._name_for(m) for m in self._macros]:
            num += 1
        name = 'macro_{}'.format(num)
        macro = {
            'name': 'Macro {}'.format(num),
            'color': [255, 0, 0],
            'steps': [
                {
                    'duration': 500,
                    'delay_after': 0,
                    'pressure': 0,
                    'ign_offset': 0,
                    'ign_dur': 300,
                    'valves': []
                }
            ],
            'finishing_step': None
        }
        save(name, macro)
        self._refresh()
        return MacroEditScreen(name, macro, self)

    def _name_for(self, filename):
        try:
            from macro_store import load
            m = load(filename)
            return m.get('name', filename)
        except:
            return filename


# --- Assign Screen ---

class AssignScreen(Screen):
    def __init__(self, macro_name, home, macro_list):
        super().__init__()
        self.macro_name = macro_name
        self.home = home
        self.macro_list = macro_list
        self._display_name = self._get_display_name()
        self.cursor = 2

    def _get_display_name(self):
        try:
            from macro_store import load
            m = load(self.macro_name)
            return m.get('name', self.macro_name)
        except:
            return self.macro_name

    def items(self):
        return [
            self._display_name,
            'Assign to aux btn?',
            'Yes',
            'No'
        ]

    def on_scroll(self, delta):
        old = self.cursor
        if delta > 0:
            if self.cursor == 0:
                self.cursor = 2
            elif self.cursor < 3:
                self.cursor = 3
        elif delta < 0:
            if self.cursor == 3:
                self.cursor = 2
            elif self.cursor == 2:
                self.cursor = 0
        if self.cursor != old:
            self.mark_dirty()

    def on_click(self, index):
        if index == 0:
            from macro_store import load
            macro = load(self.macro_name)
            return MacroEditScreen(self.macro_name, macro, self.macro_list)
        if index == 2:  # Yes
            self.home.aux_macro_name = self._display_name
            try:
                from macro_store import load
                m = load(self.macro_name)
                self.home.aux_macro_color = m.get('color', None)
            except:
                self.home.aux_macro_color = None
            return 'home'
        if index == 3:  # No
            return 'pop'
        return None


# --- Macro Edit Screen ---

class MacroEditScreen(Screen):
    def __init__(self, filename, macro, macro_list):
        super().__init__()
        self.filename = filename
        self.macro = macro
        self.macro_list = macro_list

    def items(self):
        rows = [
            'Name: ' + self.macro.get('name', '?'),
            'LED: ' + self._color_name(),
        ]
        for i, step in enumerate(self.macro['steps']):
            dur = step.get('duration', 0)
            n_valves = len(step.get('valves', []))
            rows.append('Step {} ({}ms, {}v)'.format(i + 1, dur, n_valves))
        rows.append('Add Step')

        fin = self.macro.get('finishing_step')
        if fin:
            dur = fin.get('duration', 0)
            n_valves = len(fin.get('valves', []))
            rows.append('Finish ({}ms, {}v)'.format(dur, n_valves))
        else:
            rows.append('Finish: (none)')

        if self.filename != 'main_poof':
            rows.append('Delete Macro')
        rows.append('Save & Back')
        return rows

    def _color_name(self):
        c = self.macro.get('color', [255, 0, 0])
        if c == 'rainbow':
            return 'Rainbow'
        for name, rgb in COLORS:
            if rgb == 'rainbow':
                continue
            if list(rgb) == c:
                return name
        return 'Custom'

    def on_click(self, index):
        if index == 0:
            return NameEditScreen(
                self.macro.get('name', ''),
                on_save=lambda n: self._set_name(n)
            )
        if index == 1:
            return ColorPickerScreen(
                self.macro.get('color', [255, 0, 0]),
                on_save=lambda c: self._set_color(c)
            )
        step_count = len(self.macro['steps'])
        if 2 <= index < 2 + step_count:
            step_idx = index - 2
            return StepEditScreen(self.macro, step_idx)
        if index == 2 + step_count:  # Add Step
            self.macro['steps'].append({
                'duration': 500,
                'delay_after': 0,
                'pressure': 0,
                'ign_offset': 0,
                'ign_dur': 300,
                'valves': []
            })
            self.mark_dirty()
            return StepEditScreen(self.macro, len(self.macro['steps']) - 1)

        items = self.items()
        if items[index].startswith('Finish'):
            return FinishingStepScreen(self.macro)
        if items[index] == 'Delete Macro':
            return DeleteConfirmScreen(self.filename, self.macro_list)
        if items[index] == 'Save & Back':
            from macro_store import save
            from macro_sync import request_sync
            save(self.filename, self.macro)
            request_sync()
            if self.macro_list:
                self.macro_list._refresh()
            return 'pop'
        return None

    def _set_name(self, name):
        self.macro['name'] = name
        self.mark_dirty()

    def _set_color(self, color):
        if color == 'rainbow':
            self.macro['color'] = 'rainbow'
        else:
            self.macro['color'] = list(color)
        self.mark_dirty()


# --- Delete Confirm Screen ---

class DeleteConfirmScreen(Screen):
    def __init__(self, filename, macro_list):
        super().__init__()
        self.filename = filename
        self.macro_list = macro_list
        self.cursor = 3

    def items(self):
        return [
            'Delete macro?',
            'Cannot be undone!',
            'Yes, delete',
            'No, keep it'
        ]

    def on_scroll(self, delta):
        old = self.cursor
        if delta > 0 and self.cursor < 3:
            self.cursor = 3
        elif delta < 0 and self.cursor > 2:
            self.cursor = 2
        if self.cursor != old:
            self.mark_dirty()

    def on_click(self, index):
        if index == 2:  # Yes
            from macro_store import delete
            from macro_sync import request_sync
            delete(self.filename)
            request_sync()
            if self.macro_list:
                self.macro_list._refresh()
            return 'home'
        if index == 3:  # No
            return 'pop'
        return None


# --- Color Picker Screen ---

class ColorPickerScreen(Screen):
    def __init__(self, current, on_save=None):
        super().__init__()
        self.on_save = on_save
        for i, (name, rgb) in enumerate(COLORS):
            if current == 'rainbow' and rgb == 'rainbow':
                self.cursor = i
                break
            elif rgb != 'rainbow' and list(rgb) == current:
                self.cursor = i
                break

    def items(self):
        return [name for name, _ in COLORS]

    def on_click(self, index):
        if self.on_save:
            self.on_save(COLORS[index][1])
        return 'pop'


# --- Step Edit Screen ---

class StepEditScreen(Screen):
    def __init__(self, macro, step_idx):
        super().__init__()
        self.macro = macro
        self.step_idx = step_idx

    @property
    def step(self):
        return self.macro['steps'][self.step_idx]

    def items(self):
        s = self.step
        rows = [
            'Duration: {}ms'.format(s.get('duration', 0)),
            'Delay after: {}ms'.format(s.get('delay_after', 0)),
            'Pressure: {}psi'.format(s.get('pressure', 0)),
            'Ign dur: {}ms'.format(s.get('ign_dur', 0)),
            'Ign offset: {}ms'.format(s.get('ign_offset', 0)),
        ]
        for v in s.get('valves', []):
            vtype = 'NC' if v <= 4 else 'NO'
            rows.append('Valve {} ({})'.format(v, vtype))
        rows.append('Add Valve')
        if len(self.macro['steps']) > 1:
            rows.append('Remove Step')
        rows.append('Done')
        return rows

    def on_click(self, index):
        s = self.step

        if index == 0:  # Duration
            return ValueEditScreen('Step Duration', s.get('duration', 0),
                50, 10000, 50, 'ms',
                on_save=lambda v: self._set('duration', v))
        if index == 1:  # Delay after
            return ValueEditScreen('Delay After', s.get('delay_after', 0),
                0, 5000, 50, 'ms',
                on_save=lambda v: self._set('delay_after', v))
        if index == 2:  # Pressure
            return ValueEditScreen('Pressure Threshold', s.get('pressure', 0),
                0, 200, 5, 'psi',
                on_save=lambda v: self._set('pressure', v))
        if index == 3:  # Ign dur
            return ValueEditScreen('Igniter Duration', s.get('ign_dur', 0),
                0, 1000, 50, 'ms',
                on_save=lambda v: self._set('ign_dur', v))
        if index == 4:  # Ign offset
            return ValueEditScreen('Igniter Offset', s.get('ign_offset', 0),
                0, 1000, 10, 'ms',
                on_save=lambda v: self._set('ign_offset', v))

        valve_start = 5
        valve_count = len(s.get('valves', []))
        if valve_start <= index < valve_start + valve_count:
            # Click on a valve — remove it
            valve_idx = index - valve_start
            s['valves'].pop(valve_idx)
            self.mark_dirty()
            return None
        if index == valve_start + valve_count:  # Add Valve
            return ValveSelectScreen(s)

        items = self.items()
        if items[index] == 'Remove Step':
            self.macro['steps'].pop(self.step_idx)
            return 'pop'
        if items[index] == 'Done':
            return 'pop'
        return None

    def _set(self, key, value):
        self.step[key] = value
        self.mark_dirty()


# --- Finishing Step Screen ---

class FinishingStepScreen(Screen):
    def __init__(self, macro):
        super().__init__()
        self.macro = macro

    def _get_step(self):
        return self.macro.get('finishing_step')

    def items(self):
        s = self._get_step()
        if s is None:
            return ['No finishing step', 'Add finishing step', 'Done']

        rows = [
            'Duration: {}ms'.format(s.get('duration', 0)),
            'Pressure: {}psi'.format(s.get('pressure', 0)),
            'Ign dur: {}ms'.format(s.get('ign_dur', 0)),
            'Ign offset: {}ms'.format(s.get('ign_offset', 0)),
        ]
        for v in s.get('valves', []):
            vtype = 'NC' if v <= 4 else 'NO'
            rows.append('Valve {} ({})'.format(v, vtype))
        rows.append('Add Valve')
        rows.append('Remove Finish')
        rows.append('Done')
        return rows

    def on_click(self, index):
        s = self._get_step()
        if s is None:
            if index == 1:  # Add
                self.macro['finishing_step'] = {
                    'duration': 300,
                    'delay_after': 0,
                    'pressure': 0,
                    'ign_offset': 0,
                    'ign_dur': 300,
                    'valves': []
                }
                self.mark_dirty()
                return None
            if index == 2:  # Done
                return 'pop'
            return None

        if index == 0:  # Duration
            return ValueEditScreen('Finish Duration', s.get('duration', 0),
                50, 10000, 50, 'ms',
                on_save=lambda v: self._set('duration', v))
        if index == 1:  # Pressure
            return ValueEditScreen('Pressure Threshold', s.get('pressure', 0),
                0, 200, 5, 'psi',
                on_save=lambda v: self._set('pressure', v))
        if index == 2:  # Ign dur
            return ValueEditScreen('Igniter Duration', s.get('ign_dur', 0),
                0, 1000, 50, 'ms',
                on_save=lambda v: self._set('ign_dur', v))
        if index == 3:  # Ign offset
            return ValueEditScreen('Igniter Offset', s.get('ign_offset', 0),
                0, 1000, 10, 'ms',
                on_save=lambda v: self._set('ign_offset', v))

        valve_start = 4
        valve_count = len(s.get('valves', []))
        if valve_start <= index < valve_start + valve_count:
            valve_idx = index - valve_start
            s['valves'].pop(valve_idx)
            self.mark_dirty()
            return None
        if index == valve_start + valve_count:  # Add Valve
            return ValveSelectScreen(s)

        items = self.items()
        if items[index] == 'Remove Finish':
            self.macro['finishing_step'] = None
            self.mark_dirty()
            return None
        if items[index] == 'Done':
            return 'pop'
        return None

    def _set(self, key, value):
        s = self._get_step()
        if s:
            s[key] = value
            self.mark_dirty()


# --- Valve Select Screen ---

class ValveSelectScreen(Screen):
    def __init__(self, step):
        super().__init__()
        self.step_data = step
        existing = step.get('valves', [])
        self._available = [i for i in range(1, 9) if i not in existing]

    def items(self):
        rows = []
        for v in self._available:
            vtype = 'NC' if v <= 4 else 'NO'
            rows.append('Valve {} ({})'.format(v, vtype))
        if not rows:
            rows.append('All valves assigned')
        rows.append('Done')
        return rows

    def on_click(self, index):
        if index < len(self._available):
            valve_num = self._available[index]
            self.step_data.setdefault('valves', []).append(valve_num)
            self._available.remove(valve_num)
            self.mark_dirty()
            return None
        return 'pop'


# --- LED Settings Screen ---

class LEDSettingsScreen(Screen):
    def __init__(self):
        super().__init__()

    def items(self):
        from leds import get_ring_pattern, get_ring_brightness, get_aux_brightness
        from display import lcd
        bl = 'On' if lcd.get_backlight() else 'Off'
        return [
            'Ring: {}'.format(get_ring_pattern()),
            'Ring Bright: {}%'.format(get_ring_brightness()),
            'Aux Bright: {}%'.format(get_aux_brightness()),
            'Backlight: {}'.format(bl),
        ]

    def on_click(self, index):
        from leds import PATTERNS, get_ring_pattern, get_ring_brightness
        from leds import get_aux_brightness, set_ring_pattern
        from leds import set_ring_brightness, set_aux_brightness
        from display import lcd

        if index == 0:
            # Ring pattern
            cur = PATTERNS.index(get_ring_pattern()) if get_ring_pattern() in PATTERNS else 0
            return ChoiceScreen('Ring Pattern', PATTERNS, cur,
                on_save=lambda i: self._set_pattern(PATTERNS[i]))
        if index == 1:
            # Ring brightness
            return ValueEditScreen('Ring Brightness', get_ring_brightness(),
                0, 100, 10, '%',
                on_save=lambda v: self._set_ring_bri(v))
        if index == 2:
            # Aux brightness
            return ValueEditScreen('Aux Brightness', get_aux_brightness(),
                0, 100, 10, '%',
                on_save=lambda v: self._set_aux_bri(v))
        if index == 3:
            # Backlight toggle
            if lcd.get_backlight():
                lcd.no_backlight()
                self._save_setting('backlight', False)
            else:
                lcd.backlight()
                self._save_setting('backlight', True)
            self.mark_dirty()
            return None
        return None

    def _save_setting(self, key, value):
        import settings
        settings.set(key, value)
        settings.save()

    def _set_pattern(self, pattern):
        from leds import set_ring_pattern
        set_ring_pattern(pattern)
        self._save_setting('ring_pattern', pattern)
        self.mark_dirty()

    def _set_ring_bri(self, val):
        from leds import set_ring_brightness
        set_ring_brightness(val)
        self._save_setting('ring_brightness', val)
        self.mark_dirty()

    def _set_aux_bri(self, val):
        from leds import set_aux_brightness
        set_aux_brightness(val)
        self._save_setting('aux_brightness', val)
        self.mark_dirty()


# --- Battery Screen ---

class BatteryScreen(Screen):
    def __init__(self, home=None):
        super().__init__()
        self.home = home
        self._last_values = None

    def items(self):
        from battery import percent_1s, percent_3s
        h = self.home

        # Control box battery is always local
        ctrl_pct = percent_1s(h.batt_ctrl) if h.batt_ctrl > 0 else 0
        ctrl_str = '{}mV  {}%'.format(h.batt_ctrl, ctrl_pct) if h.batt_ctrl > 0 else '--'

        if h is None or not h.connected:
            rows = [
                'Ctrl:  {}'.format(ctrl_str),
                'Ign:   --',
                'Valve: --',
                'Done'
            ]
        else:
            ign_pct = percent_1s(h.batt_ign)
            valve_pct = percent_3s(h.batt_valve)
            ign_str = '{}mV  {}%'.format(h.batt_ign, ign_pct) if h.batt_ign > 0 else '--'
            valve_str = '{}mV  {}%'.format(h.batt_valve, valve_pct) if h.batt_valve > 0 else '--'
            rows = [
                'Ctrl:  {}'.format(ctrl_str),
                'Ign:   {}'.format(ign_str),
                'Valve: {}'.format(valve_str),
                'Done'
            ]

        # Auto-refresh when values change
        cur = (h.batt_ctrl, h.batt_ign, h.batt_valve, h.connected)
        if cur != self._last_values:
            self._last_values = cur
            self.mark_dirty()

        return rows

    def on_click(self, index):
        if self.items()[index] == 'Done':
            return 'pop'
        return None


# --- Settings Screen ---

class SettingsScreen(Screen):
    def __init__(self, home=None):
        super().__init__()
        self.home = home
        self._items = [
            'LED Settings',
            'Battery Monitor',
            'WiFi / Update',
            'Reset'
        ]

    def items(self):
        return self._items

    def on_click(self, index):
        if self._items[index] == 'LED Settings':
            return LEDSettingsScreen()
        if self._items[index] == 'Battery Monitor':
            return BatteryScreen(self.home)
        return PlaceholderScreen(self._items[index])


# --- Placeholder Screen ---

class PlaceholderScreen(Screen):
    def __init__(self, title):
        super().__init__()
        self._title = title

    def items(self):
        return [self._title, '(coming soon)']

    def on_click(self, index):
        return None


# --- Menu Manager ---

class Menu:
    def __init__(self):
        self.home = HomeScreen()
        self.stack = [self.home]
        self._force_redraw = True
        self._enc_accum = 0

    @property
    def active(self):
        return self.stack[-1]

    def push(self, screen):
        self.stack.append(screen)
        self._force_redraw = True

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.active.mark_dirty()
            self._force_redraw = True

    def pop_to_home(self):
        self.stack = [self.home]
        self.home.mark_dirty()
        self._force_redraw = True

    def update(self, enc_delta, enc_click, aux_click):
        self._enc_accum += enc_delta

        if abs(self._enc_accum) >= 3:
            d = 1 if self._enc_accum > 0 else -1
            self.active.on_scroll(d)
            self._enc_accum = 0

        if enc_click:
            result = self.active.on_click(self.active.cursor)
            if result == 'pop':
                self.pop()
            elif result == 'home':
                self.pop_to_home()
            elif result is not None:
                self.push(result)

        if aux_click:
            if hasattr(self.active, 'on_back'):
                if self.active.on_back():
                    self.pop()
            else:
                self.pop()

        if self._force_redraw:
            self.active.mark_dirty()
            self._force_redraw = False

        self.active.draw()