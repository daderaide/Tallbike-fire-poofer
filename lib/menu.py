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
# Scroll to change a value, click to confirm

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
# Scroll through options, click to select

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
            return False  # don't pop
        if self.on_save:
            self.on_save(''.join(self._chars).strip())
        return True  # pop


# --- Home Screen ---

class HomeScreen(Screen):
    def __init__(self):
        super().__init__()
        self.state = 0
        self.error = 0
        self.pressure = 0
        self.batt_v = 0
        self.connected = False
        self.aux_macro_name = '(none)'

    def items(self):
        from display import STATE_NAMES, ERROR_NAMES
        if not self.connected:
            return ['THE FUPA', 'No relay box', 'Macro: ' + self.aux_macro_name, 'Settings']

        state_name = STATE_NAMES.get(self.state, '???')
        line1 = '{} | {}psi'.format(state_name, self.pressure)
        line2 = 'Batt: {}mV'.format(self.batt_v)

        if self.error > 0:
            line2 = ERROR_NAMES.get(self.error, '???')

        return [line1, line2, 'Macro: ' + self.aux_macro_name, 'Settings']

    def update_status(self, state, error, pressure, batt_v):
        changed = (state != self.state or error != self.error or
                   pressure != self.pressure or batt_v != self.batt_v)
        self.state = state
        self.error = error
        self.pressure = pressure
        self.batt_v = batt_v
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
            return SettingsScreen()
        return None


# --- Macro List Screen ---

class MacroListScreen(Screen):
    def __init__(self, home):
        super().__init__()
        self.home = home
        self._refresh()

    def _refresh(self):
        from macros import list_macros
        self._macros = list_macros()
        self.mark_dirty()

    def items(self):
        rows = ['New Macro']
        for name in self._macros:
            rows.append(name)
        return rows

    def on_click(self, index):
        if index == 0:
            return self._create_new()
        name = self._macros[index - 1]
        if name == 'main_poof':
            from macros import load
            macro = load(name)
            return MacroEditScreen(name, macro, self)
        else:
            return AssignScreen(name, self.home, self)


# --- Create new macro with auto-incremented name ---

    def _create_new(self):
        from macros import save, load
        num = 1
        while 'Macro {}'.format(num) in [self._name_for(m) for m in self._macros]:
            num += 1
        name = 'macro_{}'.format(num)
        macro = {
            'name': 'Macro {}'.format(num),
            'color': [255, 0, 0],
            'steps': [
                {
                    'trigger': 'press',
                    'pressure': 0,
                    'delay_after': 0,
                    'valves': []
                }
            ]
        }
        save(name, macro)
        self._refresh()
        return MacroEditScreen(name, macro, self)

    def _name_for(self, filename):
        try:
            from macros import load
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
            from macros import load
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
        if delta > 0 and self.cursor < 3:
            self.cursor = 3
        elif delta < 0 and self.cursor > 2:
            self.cursor = 2
        if self.cursor != old:
            self.mark_dirty()

    def on_click(self, index):
        if index == 0:
            from macros import load
            macro = load(self.macro_name)
            return MacroEditScreen(self.macro_name, macro, self.macro_list)
        if index == 2:  # Yes
            self.home.aux_macro_name = self._display_name
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
            trigger = step.get('trigger', '?')
            n_valves = len(step.get('valves', []))
            rows.append('Step {} ({}, {}v)'.format(i + 1, trigger, n_valves))
        rows.append('Add Step')
        rows.append('Save & Back')
        return rows

    def _color_name(self):
        c = self.macro.get('color', [255, 0, 0])
        for name, rgb in COLORS:
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
                'trigger': 'immediate',
                'pressure': 0,
                'delay_after': 0,
                'valves': []
            })
            self.mark_dirty()
            return StepEditScreen(self.macro, len(self.macro['steps']) - 1)
        if index == 3 + step_count:  # Save & Back
            from macros import save
            save(self.filename, self.macro)
            if self.macro_list:
                self.macro_list._refresh()
            return 'pop'
        return None

    def _set_name(self, name):
        self.macro['name'] = name
        self.mark_dirty()

    def _set_color(self, color):
        self.macro['color'] = list(color)
        self.mark_dirty()


# --- Color Picker Screen ---

class ColorPickerScreen(Screen):
    def __init__(self, current, on_save=None):
        super().__init__()
        self.on_save = on_save
        for i, (name, rgb) in enumerate(COLORS):
            if list(rgb) == current:
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
        trigger = s.get('trigger', 'press')
        rows = [
            'Trigger: {}'.format(trigger),
            'Pressure: {}psi'.format(s.get('pressure', 0)),
            'Delay after: {}ms'.format(s.get('delay_after', 0)),
        ]
        for v in s.get('valves', []):
            vtype = 'NC' if v['valve'] <= 4 else 'NO'
            dur = v.get('duration', 0)
            dur_str = 'held' if dur == 'held' else '{}ms'.format(dur)
            rows.append('V{} ({}) {}'.format(v['valve'], vtype, dur_str))
        rows.append('Add Valve')
        rows.append('Done')
        return rows

    def on_click(self, index):
        s = self.step
        triggers = ['press', 'release', 'immediate']

        if index == 0:  # Trigger
            cur = triggers.index(s.get('trigger', 'press')) if s.get('trigger', 'press') in triggers else 0
            return ChoiceScreen('Step Trigger', triggers, cur,
                on_save=lambda i: self._set('trigger', triggers[i]))
        if index == 1:  # Pressure
            return ValueEditScreen('Pressure Threshold', s.get('pressure', 0),
                0, 200, 5, 'psi',
                on_save=lambda v: self._set('pressure', v))
        if index == 2:  # Delay after
            return ValueEditScreen('Delay After', s.get('delay_after', 0),
                0, 5000, 50, 'ms',
                on_save=lambda v: self._set('delay_after', v))

        valve_count = len(s.get('valves', []))
        if 3 <= index < 3 + valve_count:
            valve_idx = index - 3
            return ValveEditScreen(s, valve_idx)
        if index == 3 + valve_count:  # Add Valve
            return ValveSelectScreen(s)
        if index == 4 + valve_count:  # Done
            return 'pop'
        return None

    def _set(self, key, value):
        self.step[key] = value
        self.mark_dirty()


# --- Valve Select Screen (pick which valve to add) ---

class ValveSelectScreen(Screen):
    def __init__(self, step):
        super().__init__()
        self.step_data = step
        existing = [v['valve'] for v in step.get('valves', [])]
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
            if valve_num <= 4:
                new_valve = {'valve': valve_num, 'duration': 200, 'ign_dur': 100, 'ign_offset': -20}
            else:
                new_valve = {'valve': valve_num, 'duration': 500}
            self.step_data.setdefault('valves', []).append(new_valve)
            self._available.remove(valve_num)
            self.mark_dirty()
            return None  # stay on screen to add more
        return 'pop'


# --- Valve Edit Screen ---

class ValveEditScreen(Screen):
    def __init__(self, step, valve_idx):
        super().__init__()
        self.step_data = step
        self.valve_idx = valve_idx

    @property
    def valve(self):
        return self.step_data['valves'][self.valve_idx]

    def items(self):
        v = self.valve
        vtype = 'NC' if v['valve'] <= 4 else 'NO'
        dur = v.get('duration', 0)
        dur_str = 'held' if dur == 'held' else '{}ms'.format(dur)

        rows = [
            'Valve {} ({})'.format(v['valve'], vtype),
            'Duration: {}'.format(dur_str),
        ]
        if v['valve'] <= 4:
            rows.append('Ign dur: {}ms'.format(v.get('ign_dur', 100)))
            rows.append('Ign offset: {}ms'.format(v.get('ign_offset', -20)))
        rows.append('Remove Valve')
        rows.append('Done')
        return rows

    def on_click(self, index):
        v = self.valve
        if index == 1:  # Duration
            if v.get('duration') == 'held':
                cur = 0
            else:
                cur = 1
            return ChoiceScreen('Valve Duration', ['While held', 'Timed'],
                cur, on_save=lambda i: self._set_dur_mode(i))
        if v['valve'] <= 4:
            if index == 2:  # Ign dur
                return ValueEditScreen('Igniter Duration',
                    v.get('ign_dur', 100), 10, 1000, 10, 'ms',
                    on_save=lambda val: self._set('ign_dur', val))
            if index == 3:  # Ign offset
                return ValueEditScreen('Igniter Offset',
                    v.get('ign_offset', -20), -500, 500, 5, 'ms',
                    on_save=lambda val: self._set('ign_offset', val))

        items = self.items()
        if items[index] == 'Remove Valve':
            self.step_data['valves'].pop(self.valve_idx)
            return 'pop'
        if items[index] == 'Done':
            return 'pop'
        return None

    def _set_dur_mode(self, choice):
        if choice == 0:
            self.valve['duration'] = 'held'
        else:
            if self.valve.get('duration') == 'held':
                self.valve['duration'] = 200
        self.mark_dirty()

    def _set(self, key, value):
        self.valve[key] = value
        self.mark_dirty()


# --- Settings Screen ---

class SettingsScreen(Screen):
    def __init__(self):
        super().__init__()
        self._items = [
            'LED Settings',
            'Battery Monitor',
            'WiFi / Update',
            'Reset'
        ]

    def items(self):
        return self._items

    def on_click(self, index):
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