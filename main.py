#!/usr/bin/env python3

from time import sleep

import ubinascii
from lcd_i2c import LCD
from machine import I2C, SPI, Pin

# from neopixel import NeoPixel

# pixel_pin = Pin(38)  # Example pin, change to your board's NeoPixel pin
# num_pixels = 1  # Number of LEDs in your strip/pixel

# np = NeoPixel(pixel_pin, num_pixels)

# # --- Blinking Loop ---
# while True:
#     # Turn pixel ON (e.g., Red)
#     np[0] = (10, 0, 10)  # RGB tuple for Red
#     np.write()  # Send data to the LED
#     sleep(0.5)  # Wait for half a second

#     # Turn pixel OFF (Black)
#     np[0] = (0, 0, 0)  # RGB tuple for Black
#     np.write()  # Send data to the LED
#     sleep(0.5)  # Wait for half a second


# PCF8574 on 0x27
I2C_ADDR = 0x27     # DEC 39, HEX 0x27
I2C_NUM_ROWS = 4
I2C_NUM_COLS = 20
FREQ = 800000   # Try lowering this value in case of "Errno 5"

# define custom I2C interface, default is 'I2C(0)'
# check the docs of your device for further details and pin infos
i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=FREQ)
lcd = LCD(addr=I2C_ADDR, cols=I2C_NUM_COLS, rows=I2C_NUM_ROWS, i2c=i2c)


def print_and_wait(text: str, sleep_time: int = 2) -> None:
    """
    Print to console and wait some time.

    :param      text:        The text to print to console
    :type       text:        str
    :param      sleep_time:  The sleep time in seconds
    :type       sleep_time:  int
    """
    print(text)
    sleep(sleep_time)


# get LCD infos/properties
print("LCD is on I2C address {}".format(lcd.addr))
print("LCD has {} columns and {} rows".format(lcd.cols, lcd.rows))
print("LCD is used with a charsize of {}".format(lcd.charsize))
print("Cursor position is {}".format(lcd.cursor_position))

# start LCD, not automatically called during init to be Arduino compatible
lcd.begin()

# print text on sceen at first row, starting on first column
lcd.print("Hello World")
print_and_wait("Show 'Hello World' on LCD")

# turn LCD off
lcd.no_backlight()
print_and_wait("Turn LCD backlight off")

# get current backlight value
print("Backlight value: {}".format(lcd.get_backlight()))

# turn LCD on
lcd.backlight()
print_and_wait("Turn LCD backlight on")

# get current backlight value
print("Backlight value: {}".format(lcd.get_backlight()))

# clear LCD display content
lcd.clear()
print_and_wait("Clear display content")

# turn cursor on (show)
lcd.cursor()
print_and_wait("Turn cursor on (show)")

# blink cursor
lcd.blink()
print_and_wait("Blink cursor")

# return cursor to home position
lcd.home()
print_and_wait("Return cursor to home position")

# stop blinking cursor
lcd.no_blink()
print_and_wait("Stop blinking cursor")

# turn cursor off (hide)
lcd.no_cursor()
print_and_wait("Turn cursor off (hide)")

# print_and_wait text on sceen
lcd.print("Hello again")
print_and_wait("Show 'Hello again' on LCD")

# turn display off
lcd.no_display()
print_and_wait("Turn LCD off")

# turn display on
lcd.display()
print_and_wait("Turn LCD on")

# scroll display to the left
for _ in "Hello again":
    lcd.scroll_display_left()
    sleep(0.5)
print_and_wait("Scroll display to the left")

# scroll display to the right
for _ in "Hello again":
    lcd.scroll_display_right()
    sleep(0.5)
print_and_wait("Scroll display to the right")

# set text flow right to left
lcd.clear()
lcd.set_cursor(col=12, row=0)
lcd.right_to_left()
lcd.print("Right to left")
print_and_wait("Set text flow right to left")

# set text flow left to right
lcd.clear()
lcd.set_cursor(col=0, row=0)
lcd.left_to_right()
lcd.print("Left to right")
print_and_wait("Set text flow left to right")

# activate autoscroll
lcd.autoscroll()
print_and_wait("Activate autoscroll")

# disable autoscroll
lcd.no_autoscroll()
print_and_wait("Disable autoscroll")

# set cursor to second line, seventh column
lcd.clear()
lcd.cursor()
# lcd.cursor_position = (7, 1)
lcd.set_cursor(col=7, row=1)
print_and_wait("Set cursor to row 1, column 7")
lcd.no_cursor()

# set custom char number 0 as :-)
# custom char can be set for location 0 ... 7
lcd.create_char(
    location=0,
    charmap=[0x00, 0x00, 0x11, 0x04, 0x04, 0x11, 0x0E, 0x00]
    # this is the binary matrix, feel it, see it
    # 00000
    # 00000
    # 10001
    # 00100
    # 00100
    # 10001
    # 01110
    # 00000
)
print_and_wait("Create custom char ':-)'")

# show custom char stored at location 0
lcd.print(chr(0))
lcd.print(chr(0))
print_and_wait("Show custom char")


# Initialize SPI and CS pin once (more efficient for continuous reading)
spi = SPI(1, baudrate=1000000, polarity=0, phase=1)
cs = Pin(10, Pin.OUT)
cs.off()  # Start with CS low

def read_knob():
    """Read knob value via SPI."""
    cs.off()  # Select device
    spi.write(bytearray([0xFF, 0xFF]))
    cs.on()   # Deselect
    cs.off()  # Select again for read
    result = spi.read(2)
    cs.on()   # Deselect
    return ubinascii.hexlify(result)


# ============================================================================
# CONTINUOUS READING OPTIONS
# ============================================================================

# Option 1: Simple polling loop (blocks everything else)
def continuous_read_simple():
    """Simple continuous reading - blocks other operations."""
    while True:
        value = read_knob()
        print(f"Knob value: {value}")
        # Process value here
        # sleep(0.01)  # Optional: small delay to prevent overwhelming


# Option 2: Timer-based polling (allows other tasks to run)
def continuous_read_timer():
    """Continuous reading using Timer - non-blocking."""
    from machine import Timer
    
    last_value = None
    
    def read_callback(timer):
        nonlocal last_value
        value = read_knob()
        if value != last_value:  # Only process if changed
            last_value = value
            print(f"Knob value: {value}")
            # Process value here
            # Update LCD, etc.
    
    # Create timer that calls read_callback every 10ms (100Hz)
    timer = Timer(-1)  # Virtual timer
    timer.init(period=10, mode=Timer.PERIODIC, callback=read_callback)
    return timer


# Option 3: Asyncio-based (best for complex applications)
# Requires: import uasyncio as asyncio
async def continuous_read_async():
    """Continuous reading using asyncio - most flexible."""
    try:
        import uasyncio as asyncio
    except ImportError:
        print("uasyncio not available, use timer-based approach")
        return
    
    while True:
        value = read_knob()
        print(f"Knob value: {value}")
        # Process value here
        await asyncio.sleep_ms(10)  # Read every 10ms


# Option 4: Threading (if supported on your MicroPython port)
def continuous_read_thread():
    """Continuous reading in a separate thread."""
    import _thread
    
    def read_loop():
        while True:
            value = read_knob()
            print(f"Knob value: {value}")
            # Process value here
            sleep(0.01)
    
    _thread.start_new_thread(read_loop, ())


# Option 5: Practical example - Read knob and update LCD
def continuous_read_with_lcd(lcd_instance):
    """Read knob continuously and update LCD display."""
    from machine import Timer
    
    def update_display(timer):
        value = read_knob()
        # Convert hex to readable format (adjust based on your device)
        try:
            # Example: convert hex bytes to integer
            int_value = int(value, 16)
            # Update LCD
            lcd_instance.clear()
            lcd_instance.set_cursor(0, 0)
            lcd_instance.print(f"Knob: {int_value}")
            lcd_instance.set_cursor(0, 1)
            lcd_instance.print(f"Hex: {value.decode()}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Read and update every 50ms (20Hz - good for knob reading)
    timer = Timer(-1)
    timer.init(period=50, mode=Timer.PERIODIC, callback=update_display)
    return timer


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

# To start continuous reading, choose one:

# Example 1: Simple blocking loop (uncomment to use)
# continuous_read_simple()

# Example 2: Timer-based (recommended - non-blocking)
# timer = continuous_read_timer()
# # Your other code can run here
# # To stop: timer.deinit()

# Example 3: With LCD updates
# timer = continuous_read_with_lcd(lcd)
# # Your other code can run here
# # To stop: timer.deinit()

# Example 4: Asyncio (if you want to use async/await)
# import uasyncio as asyncio
# asyncio.run(continuous_read_async())
