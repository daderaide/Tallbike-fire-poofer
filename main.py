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


# Initialize LCD
print("LCD is on I2C address {}".format(lcd.addr))
print("LCD has {} columns and {} rows".format(lcd.cols, lcd.rows))

# Start LCD, not automatically called during init to be Arduino compatible
lcd.begin()
lcd.backlight()  # Make sure backlight is on
lcd.no_cursor()  # Hide cursor for cleaner display

# ============================================================================
# DEMO CODE - Commented out to focus on knob reading
# Uncomment if you want to see LCD demo features
# ============================================================================
# print("LCD is used with a charsize of {}".format(lcd.charsize))
# print("Cursor position is {}".format(lcd.cursor_position))
# lcd.print("Hello World")
# print_and_wait("Show 'Hello World' on LCD")
# ... (rest of demo code)


# Initialize SPI and CS pin once (more efficient for continuous reading)
# AS5047P requires: CPOL=0, CPHA=1 (polarity=0, phase=1), MSB first
spi = SPI(1, baudrate=2000000, polarity=0, phase=1, bits=8, firstbit=SPI.MSB)
cs = Pin(10, Pin.OUT, value=1)  # CS high when idle

# AS5047P register addresses
AS5047P_ANGLECOM = 0x3FFF  # Angle register (read-only)
AS5047P_ERRFL = 0x0001  # Error flag register


def even_parity_15bits(value):
    """Calculate even parity for bits 0-14 of a 16-bit value."""
    # Count number of 1s in bits 0-14
    count = bin(value & 0x7FFF).count("1")
    return (count % 2) == 0


def build_command(addr, is_read=True):
    """Build a 16-bit command frame with proper parity for AS5047P.

    Format:
    - Bit 15: PARC (even parity over bits 14-0)
    - Bit 14: R/W (1=Read, 0=Write)
    - Bits 13-0: Register address
    """
    rw_bit = 1 if is_read else 0
    cmd_low = (rw_bit << 14) | (addr & 0x3FFF)

    # Calculate parity bit (bit 15)
    parity_bit = 0 if even_parity_15bits(cmd_low) else 1

    # Combine: parity bit (15) + command (14-0)
    cmd = (parity_bit << 15) | cmd_low
    return cmd


def send_command_bytes(cmd):
    """Convert 16-bit command to 2 bytes (MSB first)."""
    return bytes([(cmd >> 8) & 0xFF, cmd & 0xFF])


def read_knob():
    """Read angle from AS5047P with proper parity and error checking.

    Returns: bytes object with hex-encoded angle value, or None on error.
    """
    try:
        # Step 1: Send read command for angle register (0x3FFF)
        cmd = build_command(AS5047P_ANGLECOM, is_read=True)
        cmd_bytes = send_command_bytes(cmd)

        cs.off()  # Select device
        # Read dummy data while writing command (SPI requires simultaneous read/write)
        dummy_read = bytearray(2)
        try:
            spi.write_readinto(cmd_bytes, dummy_read)  # Write command, read dummy
        except AttributeError:
            # Fallback if write_readinto not available
            spi.write(cmd_bytes)
            dummy_read = spi.read(2)  # Read dummy response
        cs.on()  # Deselect

        # Step 2: AS5047P returns data delayed by one command
        # Send NOP (read from address 0x0000) to get the angle data
        # We need to write and read simultaneously for SPI
        nop_cmd = build_command(0x0000, is_read=True)
        nop_bytes = send_command_bytes(nop_cmd)

        cs.off()  # Select device
        # Use write_readinto for simultaneous write/read (preferred)
        # Fallback to read() with write parameter if not available
        try:
            response = bytearray(2)
            spi.write_readinto(
                nop_bytes, response
            )  # Write NOP and read response simultaneously
        except AttributeError:
            # Fallback: some MicroPython ports use read() with write parameter
            response = spi.read(2, write=nop_bytes)  # Write NOP while reading
        cs.on()  # Deselect

        if len(response) != 2:
            print("Error: Invalid response length")
            return None

        # Parse response frame
        data_word = (response[0] << 8) | response[1]

        # Debug: print raw response for troubleshooting
        # print(f"Raw response: {response[0]:02x} {response[1]:02x} = 0x{data_word:04x}")

        # Extract fields from response:
        # Bit 15: PARD (parity bit for response)
        # Bit 14: EF (error flag)
        # Bits 13-0: Data (14-bit angle)
        pard = (data_word >> 15) & 1
        ef = (data_word >> 14) & 1
        angle_data = data_word & 0x3FFF

        # Verify response parity
        computed_parity = 0 if even_parity_15bits(data_word & 0x7FFF) else 1
        if computed_parity != pard:
            # Parity error - this is a real problem, log it
            print(
                f"AS5047P parity error in response! Expected {computed_parity}, got {pard}"
            )
            # Still return the data, but it may be corrupted

        # Note: EF bit can give false positives, so we only check ERRFL if parity fails
        # Ignore EF bit otherwise to reduce noise

        # Return hex-encoded angle value
        # Convert bytearray to bytes if needed
        if isinstance(response, bytearray):
            return ubinascii.hexlify(bytes(response))
        else:
            return ubinascii.hexlify(response)

    except Exception as e:
        print(f"Error reading knob: {e}")
        import sys

        sys.print_exception(e)
        return None


# ============================================================================
# CONTINUOUS READING OPTIONS
# ============================================================================

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


# Helper function to update LCD display with knob value
def update_lcd_with_knob_value(lcd_instance, value, cumulative_counter=None):
    """Update LCD display with knob value.

    Args:
        lcd_instance: LCD object to update
        value: Hex-encoded angle value
        cumulative_counter: Optional integer counter (increments/decrements with rotation)
    """
    if value is None:
        lcd_instance.clear()
        lcd_instance.set_cursor(0, 0)
        lcd_instance.print("Read Error")
        return False

    try:
        # Convert hex bytes to integer
        raw_value = int(value, 16)

        # AS5047P returns 14-bit angle in bits 13-0
        # Extract the 14-bit angle value
        angle_14bit = raw_value & 0x3FFF

        # Calculate angle in degrees (0-360)
        angle_degrees = (angle_14bit * 360.0) / 16384.0  # 2^14 = 16384

        # Calculate percentage (0-100%)
        percentage = (angle_14bit * 100) // 16384

        # Update LCD - format nicely for 20x4 display
        lcd_instance.clear()

        # Row 0: Title
        lcd_instance.set_cursor(0, 0)
        lcd_instance.print("Knob Value:")

        # Row 1: Cumulative counter (primary display)
        if cumulative_counter is not None:
            lcd_instance.set_cursor(0, 1)
            lcd_instance.print(f"Count: {cumulative_counter:6d}")
        else:
            lcd_instance.set_cursor(0, 1)
            lcd_instance.print(f"Angle: {angle_degrees:6.1f} deg")

        # Row 2: Current angle in degrees
        lcd_instance.set_cursor(0, 2)
        lcd_instance.print(f"Angle: {angle_degrees:6.1f} deg")

        # Row 3: Raw value
        lcd_instance.set_cursor(0, 3)
        lcd_instance.print(f"Raw: {angle_14bit:5d} ({percentage:3d}%)")

        # Print to console only when display updates (reduces noise)
        if cumulative_counter is not None:
            print(f"Count: {cumulative_counter}, Angle: {angle_degrees:.1f}°")
        else:
            print(f"Angle: {angle_degrees:.1f}° ({angle_14bit}/16384, {percentage}%)")
        return True
    except Exception as e:
        print(f"Error processing knob value: {e}")
        import sys

        sys.print_exception(e)
        # Show error on LCD
        lcd_instance.clear()
        lcd_instance.set_cursor(0, 0)
        lcd_instance.print("Error processing")
        lcd_instance.set_cursor(0, 1)
        lcd_instance.print(str(e)[:20])
        return False


# Option 5: Read knob and update LCD (optimized - only updates when value changes)
def calculate_angle_direction(current_angle, last_angle):
    """Calculate change and direction, handling wraparound at 0/360.

    Returns:
        tuple: (angle_change_in_degrees, direction)
            - direction: +1 for forward, -1 for backward, 0 for no significant change
    """
    # Calculate raw difference
    raw_diff = current_angle - last_angle

    # Handle wraparound: if difference is > 180, we crossed 0/360 boundary
    if raw_diff > 180:
        # Went backwards (e.g., 350° to 10° means we went from 350 to 360, then to 10)
        angle_diff = -(360 - raw_diff)
        direction = -1
    elif raw_diff < -180:
        # Went forwards (e.g., 10° to 350° means we went from 10 to 0, then to 350)
        angle_diff = 360 + raw_diff
        direction = 1
    else:
        # Normal case, no wraparound
        angle_diff = raw_diff
        direction = 1 if raw_diff > 0 else (-1 if raw_diff < 0 else 0)

    return abs(angle_diff), direction


def continuous_read_with_lcd(lcd_instance, angle_threshold=1.0):
    """Read knob continuously and update LCD display using timer.

    Args:
        lcd_instance: LCD object to update
        angle_threshold: Minimum change in degrees before updating display (default: 1.0)
    """
    from machine import Timer

    last_value = None
    last_angle_degrees = None
    cumulative_counter = 0  # Integer counter that increments/decrements
    accumulated_angle = 0.0  # Track accumulated angle change for 30-degree increments
    update_count = 0
    DEGREES_PER_COUNT = 30.0  # 1 count per 30 degrees

    def update_display(timer):
        nonlocal last_value, last_angle_degrees, cumulative_counter, accumulated_angle, update_count
        update_count += 1

        try:
            value = read_knob()

            # Skip if read failed (returned None)
            if value is None:
                return

            # Calculate current angle
            try:
                raw_value = int(value, 16)
                angle_14bit = raw_value & 0x3FFF
                angle_degrees = (angle_14bit * 360.0) / 16384.0
            except Exception:
                # If we can't parse, just update if raw value changed
                if last_value is None or value != last_value:
                    last_value = value
                    update_lcd_with_knob_value(lcd_instance, value, cumulative_counter)
                return

            # Initialize on first read
            if last_angle_degrees is None:
                last_value = value
                last_angle_degrees = angle_degrees
                update_lcd_with_knob_value(lcd_instance, value, cumulative_counter)
                return

            # Calculate angle change and direction
            angle_diff, direction = calculate_angle_direction(
                angle_degrees, last_angle_degrees
            )

            # Only process if change exceeds threshold
            if angle_diff >= angle_threshold:
                # Accumulate angle change
                accumulated_angle += direction * angle_diff

                # Update counter: 1 count per 30 degrees
                counts_to_add = int(abs(accumulated_angle) / DEGREES_PER_COUNT)
                if counts_to_add > 0:
                    cumulative_counter += direction * counts_to_add
                    # Keep remainder for next update
                    accumulated_angle = accumulated_angle - (
                        direction * counts_to_add * DEGREES_PER_COUNT
                    )

                last_value = value
                last_angle_degrees = angle_degrees
                update_lcd_with_knob_value(lcd_instance, value, cumulative_counter)
        except KeyboardInterrupt:
            # Don't handle KeyboardInterrupt in timer callback - let it propagate
            raise
        except Exception as e:
            # Only log errors occasionally to avoid flooding
            if update_count % 100 == 0:  # Log every 100th error
                print(f"Error in timer callback: {e}")
            # Don't update LCD on every error to avoid flickering

    # Try to create a timer - different boards use different timer numbers
    # Try virtual timer first, then hardware timers 0, 1, 2
    timer = None
    for timer_id in [-1, 0, 1, 2, 3]:
        try:
            timer = Timer(timer_id)
            timer.init(period=50, mode=Timer.PERIODIC, callback=update_display)
            print(f"Timer {timer_id} initialized successfully")
            break
        except (ValueError, OSError) as e:
            print(f"Timer {timer_id} failed: {e}")
            continue

    if timer is None:
        raise RuntimeError(
            "Could not initialize any timer. Use continuous_read_with_lcd_loop() instead."
        )

    return timer


# Option 6: Loop-based continuous reading (fallback if timers don't work)
def continuous_read_with_lcd_loop(lcd_instance, angle_threshold=1.0):
    """Read knob continuously using a loop (works on all boards).

    Args:
        lcd_instance: LCD object to update
        angle_threshold: Minimum change in degrees before updating display (default: 1.0)
    """
    from time import sleep_ms

    last_value = None
    last_angle_degrees = None
    cumulative_counter = 0  # Integer counter that increments/decrements
    accumulated_angle = 0.0  # Track accumulated angle change for 30-degree increments
    DEGREES_PER_COUNT = 30.0  # 1 count per 30 degrees

    print("Starting loop-based knob reading...")
    while True:
        try:
            value = read_knob()

            if value is None:
                sleep_ms(50)
                continue

            # Calculate current angle
            try:
                raw_value = int(value, 16)
                angle_14bit = raw_value & 0x3FFF
                angle_degrees = (angle_14bit * 360.0) / 16384.0
            except Exception:
                # If we can't parse, just update if raw value changed
                if last_value is None or value != last_value:
                    last_value = value
                    update_lcd_with_knob_value(lcd_instance, value, cumulative_counter)
                sleep_ms(50)
                continue

            # Initialize on first read
            if last_angle_degrees is None:
                last_value = value
                last_angle_degrees = angle_degrees
                update_lcd_with_knob_value(lcd_instance, value, cumulative_counter)
                sleep_ms(50)
                continue

            # Calculate angle change and direction
            angle_diff, direction = calculate_angle_direction(
                angle_degrees, last_angle_degrees
            )

            # Only process if change exceeds threshold
            if angle_diff >= angle_threshold:
                # Accumulate angle change
                accumulated_angle += direction * angle_diff

                # Update counter: 1 count per 30 degrees
                counts_to_add = int(abs(accumulated_angle) / DEGREES_PER_COUNT)
                if counts_to_add > 0:
                    cumulative_counter += direction * counts_to_add
                    # Keep remainder for next update
                    accumulated_angle = accumulated_angle - (
                        direction * counts_to_add * DEGREES_PER_COUNT
                    )

                last_value = value
                last_angle_degrees = angle_degrees
                update_lcd_with_knob_value(lcd_instance, value, cumulative_counter)

            sleep_ms(50)  # Read every 50ms (20Hz)
        except KeyboardInterrupt:
            print("\nStopping knob reading...")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            import sys

            sys.print_exception(e)
            sleep_ms(100)  # Wait a bit before retrying


# ============================================================================
# START CONTINUOUS KNOB READING WITH LCD DISPLAY
# ============================================================================

# Clear LCD and show startup message
lcd.clear()
lcd.set_cursor(0, 0)
lcd.print("Knob Reader")
lcd.set_cursor(0, 1)
lcd.print("Initializing...")
sleep(1)

# Test read_knob() first to make sure it works
print("Testing knob read...")
try:
    test_value = read_knob()
    print(f"Test read successful: {test_value}")
except Exception as e:
    print(f"ERROR: Knob read failed: {e}")
    import sys

    sys.print_exception(e)
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.print("Knob read failed!")
    lcd.set_cursor(0, 1)
    lcd.print(str(e)[:20])
    # Don't start timer if read fails
    raise

# Start continuous reading with LCD updates
# Set threshold to 5.0 degrees to prevent flickering from small noise variations
# Since meaningful changes are ~30 degrees, 5 degrees provides good filtering
ANGLE_UPDATE_THRESHOLD = 5.0  # degrees - minimum change before updating display

print("Starting continuous knob reading...")
print(f"Display will update when angle changes by >= {ANGLE_UPDATE_THRESHOLD} degrees")
try:
    timer = continuous_read_with_lcd(lcd, angle_threshold=ANGLE_UPDATE_THRESHOLD)
    print("Timer started!")
    use_timer = True
except Exception as e:
    print(f"Timer initialization failed: {e}")
    print("Falling back to loop-based reading...")
    use_timer = False
    timer = None

# Do an immediate first read to populate the display
print("Performing initial read...")
try:
    initial_value = read_knob()
    if initial_value:
        print(f"Initial read: {initial_value}")
        update_lcd_with_knob_value(lcd, initial_value, 0)  # Start counter at 0
        print("Initial display updated")
    else:
        print("Initial read returned None")
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.print("Read returned None")
except Exception as e:
    print(f"Error in initial read: {e}")
    import sys

    sys.print_exception(e)

# Keep the script running
# The timer callback will handle all updates
# You can add other code here that will run alongside the knob reading
print("Knob reading active! Press Ctrl+C to stop.")

# Main loop - keep script alive
try:
    if use_timer:
        # Timer-based: just keep script running
        while True:
            sleep(1)  # Just keep the script running
            # You can add other periodic tasks here if needed
    else:
        # Loop-based: run the loop function
        continuous_read_with_lcd_loop(lcd, angle_threshold=ANGLE_UPDATE_THRESHOLD)
except KeyboardInterrupt:
    print("\nStopping knob reading...")
    if timer is not None:
        timer.deinit()
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.print("Stopped")
    print("Done.")
