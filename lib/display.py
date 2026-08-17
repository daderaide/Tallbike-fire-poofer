# display.py — LCD status display (control box only)

from hardware import i2c
from lcd_i2c import LCD

lcd = LCD(addr=0x27, cols=20, rows=4, i2c=i2c)
lcd.begin()

STATE_NAMES = {
    0: 'IDLE',
    1: 'ARMED',
    2: 'FIRING',
    3: 'ERROR'
}

ERROR_NAMES = {
    0: '',
    1: 'COMMS TIMEOUT',
    2: 'OVER PRESSURE',
    3: 'LOW BATT IGN',
    4: 'LOW BATT VALVE',
    5: 'MACRO ERROR',
    6: 'MELTDOWN IMMINENT'
}

def show_status(state, error=0, pressure=0, batt_v=0):
    state_name = STATE_NAMES.get(state, '???')

    lcd.set_cursor(0, 0)
    lcd.print('{:<20}'.format('STATE: ' + state_name))

    lcd.set_cursor(0, 1)
    lcd.print('{:<20}'.format('PSI: ' + str(pressure)))

    lcd.set_cursor(0, 2)
    lcd.print('{:<20}'.format('BATT: ' + str(batt_v) + 'mV'))

    lcd.set_cursor(0, 3)
    if error > 0:
        lcd.print('{:<20}'.format('ERR: ' + ERROR_NAMES.get(error, '???')))
    else:
        lcd.print('{:<20}'.format('THE FUPA'))

def show_no_relay():
    lcd.set_cursor(0, 0)
    lcd.print('{:<20}'.format('THE FUPA'))
    lcd.set_cursor(0, 1)
    lcd.print('{:<20}'.format('No relay box'))
    lcd.set_cursor(0, 2)
    lcd.print('{:<20}'.format(''))
    lcd.set_cursor(0, 3)
    lcd.print('{:<20}'.format(''))