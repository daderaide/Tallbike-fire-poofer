# menu.py — Screen-stack menu system (control box only)
# Encoder scrolls cursor, click selects, aux goes back

from display import lcd

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

        # Keep cursor visible in 4-line window
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


# --- Home Screen ---

class HomeScreen(Screen):
    def __init__(self):
        super().__init__()
        self.state = 0
        self.error = 0
        self.pressure = 0
        self.batt_v = 0
        self.connected = False

    def items(self):
        from display import STATE_NAMES, ERROR_NAMES
        if not self.connected:
            return ['THE FUPA', 'No relay box', '', 'Settings']

        state_name = STATE_NAMES.get(self.state, '???')
        line1 = '{} | {}psi'.format(state_name, self.pressure)
        line2 = 'Batt: {}mV'.format(self.batt_v)

        if self.error > 0:
            line3 = ERROR_NAMES.get(self.error, '???')
        else:
            line3 = 'Macro: (none)'

        return [line1, line2, line3, 'Settings']

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
        if index < len(items) and items[index] == 'Settings':
            return SettingsScreen()
        return None


# --- Settings Screen ---

class SettingsScreen(Screen):
    def __init__(self):
        super().__init__()
        self._items = [
            'Poof Settings',
            'Macro List',
            'LED Settings',
            'Battery Monitor',
            'WiFi / Update',
            'Reset'
        ]

    def items(self):
        return self._items

    def on_click(self, index):
        # Placeholder — sub-screens go here later
        return PlaceholderScreen(self._items[index])


# --- Placeholder Screen ---

class PlaceholderScreen(Screen):
    def __init__(self, title):
        super().__init__()
        self._title = title

    def items(self):
        return [self._title, '(coming soon)', '', 'Press aux to go back']

    def on_click(self, index):
        return None


# --- Menu Manager ---

class Menu:
    def __init__(self):
        self.home = HomeScreen()
        self.stack = [self.home]
        self._force_redraw = True

    @property
    def active(self):
        return self.stack[-1]

    def push(self, screen):
        self.stack.append(screen)
        self._force_redraw = True

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self._force_redraw = True

    def update(self, enc_delta, enc_click, aux_click):
        self._enc_accum = getattr(self, '_enc_accum', 0) + enc_delta

        if abs(self._enc_accum) >= 2:
            d = 1 if self._enc_accum > 0 else -1
            self.active.on_scroll(d)
            self._enc_accum = 0

        if enc_click:
            new_screen = self.active.on_click(self.active.cursor)
            if new_screen is not None:
                self.push(new_screen)

        if aux_click:
            self.pop()

        if self._force_redraw:
            self.active.mark_dirty()
            self._force_redraw = False

        self.active.draw()