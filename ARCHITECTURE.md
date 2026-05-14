# The FUPA — Poofer Control System Architecture
### *Fire Up Poof Again*

## Overview

This document defines the system architecture for the Tallbike Fire Poofer control system. The system consists of a handheld control box and a remote relay box, connected via RS-485 over an umbilical cable. The control box manages the user interface, and the relay box actuates 8 solenoid valves (4 NC poof valves + 4 NO isolation valves), reads propane pressure, monitors batteries, and controls the igniter.

The architecture is designed to be modular so that features can be added incrementally without rewriting existing code. MVP gets fire out of the bike. Everything else layers on top.

---

## Hardware Summary

### Control Box
- **MCU**: ESP32-S3-DevKitC-1-N8R8 (MicroPython)
- **Display**: 20x4 I2C LCD at `0x27`
- **Encoder**: Generic quadrature rotary encoder with pushbutton (CLK, DT, SW)
- **Main Button**: Momentary with 16-LED WS2812 NeoPixel ring
- **Aux Button**: Momentary with single WS2812 NeoPixel
- **Comms**: UART1 → MAX485 RS-485 transceiver (manual DE/RE)
- **Battery**: 2× 18650 (parallel, 1S) with ADC voltage monitor
- **Pin Assignments**:
  - I2C: SDA=GPIO13, SCL=GPIO14
  - UART1: TX=GPIO17, RX=GPIO18
  - MAX485 DE/RE: GPIO8
  - Encoder: CLK=GPIO4, DT=GPIO5, SW=GPIO6
  - Main button: GPIO7, NeoPixel=GPIO15
  - Aux button: GPIO11, NeoPixel=GPIO10
  - Battery ADC: GPIO9 (ADC1_CH8, through voltage divider, 0.6726 ratio)

### Relay Box
- **MCU**: ESP32-S3-DevKitC-1-N8R8 (MicroPython)
- **Relay Board**: PCF8574A I2C 8-relay module at `0x3F`
  - Relays 1–4: NC poof valves (normally closed, energize to open)
  - Relays 5–8: NO isolation valves (normally open, energize to close)
- **Igniter Relay**: Single digital I/O relay (separate from 8-relay board)
- **ADC**: ADS1015 at `0x48`
  - A0: Propane pressure sensor (0–500 PSI, 0.5–4.5V)
  - A1: Igniter battery monitor (1S, 4.2V max)
  - A2: Valve battery monitor (3S, 12.6V through voltage divider, 0.2966 ratio)
- **Comms**: UART1 → MAX485 RS-485 transceiver (manual DE/RE)
- **Pin Assignments**:
  - I2C: SDA=GPIO1, SCL=GPIO2
  - UART1: TX=GPIO17, RX=GPIO18
  - MAX485 DE/RE: GPIO8

---

## Module Definitions

### 1. Hardware Abstraction (`hardware.py`)
**Responsibility**: Owns all pin definitions and hardware initialization. Every other module gets its hardware access through this one.

- Defines all GPIO pin numbers, I2C bus config, UART config, SPI config
- Initializes Pin objects, I2C bus, UART, NeoPixel strips
- If a pin assignment changes, it changes here and nowhere else
- Other modules import hardware objects from this module

### 2. RS-485 Communication (`comms.py`)
**Responsibility**: Handles the serial protocol between control box and relay box.

- Manages UART read/write and DE/RE direction pin toggling
- Defines the command/response protocol (set relays, read pressure, read battery voltages, etc.)
- Handles message framing, addressing, and error detection
- Other modules call simple functions like `set_relays(bitmask)` or `read_pressure()` without knowing the serial details
- Must be reliable — this is the backbone of the whole system

### 3. Valve Controller (`valves.py`)
**Responsibility**: Core logic for firing valves. Knows about pressure lockout and valve states.

- Maintains the current state of all 8 valves
- Implements pressure lockout: checks pressure before allowing fire, configurable threshold
- In MVP: "fire all" (all 4 NC open + all 4 NO open) and "stop all"
- Later: accepts step-by-step instructions from the macro engine
- Sends relay commands through the comms module
- Controls igniter relay timing

### 4. Input Manager (`inputs.py`)
**Responsibility**: Reads and debounces all user inputs on the control box.

- Rotary encoder: rotation direction and click detection
- Main button: press/release events
- Aux button: press/release events
- Provides clean, debounced events to other modules
- Other modules ask "was the button pressed?" or "which way did the encoder turn?" without touching GPIOs

### 5. Display Manager (`display.py`)
**Responsibility**: Owns the LCD. All screen content goes through this module.

- Manages what's currently shown on the 20×4 LCD
- Provides functions to update specific regions of the display
- Handles screen refresh rate so other modules don't spam the I2C bus
- In MVP: shows pressure, ready/locked status
- Later: renders the full scrollable home screen and menu screens

### 6. LED Manager (`leds.py`)
**Responsibility**: Controls the NeoPixels on both buttons.

- Main button ring (16 LEDs on GPIO15): patterns, colors, press/release feedback
- Aux button LED (1 LED on GPIO14): color reflects current macro assignment
- Manages pre-programmed LED patterns (selectable in settings)
- In MVP: simple on/off or static color
- Later: animated patterns, context-dependent color changes

### 7. Config Manager (`config.py`)
**Responsibility**: Reads and writes persistent settings to flash storage.

- Stores all settings as JSON on the ESP32's filesystem
- Macros, pressure thresholds, LED preferences, main poof timing offsets, fuel usage counter
- Loads config on boot, writes on save (not continuously — flash wear consideration)
- Provides default values for first boot or after reset
- Reset function restores factory defaults

### 8. Battery Monitor (`battery.py`)
**Responsibility**: Reads and reports battery voltages for all three packs.

- Control box 1S (local ADC on GPIO9)
- Igniter 1S (remote, via RS-485 → ADS1015 A1)
- Valve 3S (remote, via RS-485 → ADS1015 A2, with voltage divider ratio)
- Converts raw ADC values to voltage and approximate percentage
- Generates warning flags when batteries are low
- Warnings fed to display manager for the home screen

### 9. Macro Engine (`macros.py`)
**Responsibility**: Interprets macro sequences and drives the valve controller.

- **Not in MVP** — added after core functionality is solid
- Reads macro definitions from config
- Executes step sequences: each step defines valve states and a transition condition
- Transition types:
  - **Timed**: fixed duration, then advance to next step
  - **Button-dependent**: held = stay in step, release = advance
  - **Pressure-dependent**: monitor pressure sensor, adapt timing based on feedback
  - **Loop**: return to a previous step (for repeating patterns)
  - **End**: macro complete, return to idle
- Each step can define: valve bitmask, igniter state, igniter timing offset, transition condition
- Handles the aux button: runs the currently selected macro when pressed

### 10. WiFi / OTA Manager (`wifi.py`)
**Responsibility**: Manages WiFi connectivity and WebREPL for wireless code deployment.

- **Not in MVP** — added when convenient, not critical path
- WiFi station mode (connect to existing network) or AP mode (ESP32 creates its own network)
- WebREPL server for wireless Python console and file upload to the control box
- Control box can relay file updates to the relay box over RS-485, or relay box runs its own WebREPL over the same WiFi network
- All WiFi features off by default — enabled from menu only when needed to conserve power
- SSID, password, and mode stored in config

### 11. Menu System (`menu.py`)
**Responsibility**: UI navigation, screen rendering, and user input handling for settings.

- **Not in MVP** — added after core functionality is solid
- Manages screen hierarchy and navigation state
- Encoder scrolling highlights items, encoder click selects, aux button = back
- Screens include:
  - **Home screen**: scrollable live status (pressure, fuel gauge, warnings, current aux macro)
  - **Macro list**: select/assign a macro to the aux button
  - **New macro wizard**: name → color → valve selection → per-valve configuration → save
  - **Main poof options**: timing offsets for NC valves, NO valves, igniter; pressure lockout threshold
  - **LED settings**: pattern selection for main button
  - **Battery monitor**: detailed voltage/percentage for all 3 packs
  - **WiFi / Update**: WiFi on/off, AP mode on/off, SSID, password, IP address (read-only), connection status (read-only), WebREPL on/off — enables wireless code deployment to both boards without plugging in
  - **Reset**: restore defaults with confirmation

---

## Main Screen Layout (20×4 LCD)

The home screen displays live system status. Scrolling the encoder highlights different items. Clicking the encoder drills into the relevant detail/settings screen for that item.

Selectable items on the home screen:
- System pressure (current PSI reading)
- Fuel gauge (estimated propane remaining) — click to access fuel gauge screen:
  - Reset counter (for tank swap)
  - Select tank size (denominator for percentage calculation)
  - Fuel estimation based on counted accumulator dump cycles vs. known tank volume
- Current aux macro name + color indicator
- Warning messages (low battery, etc.)

---

## Macro Data Structure (Preliminary)

Each macro consists of:
- **Name**: user-defined string
- **Button color**: RGB value for the aux button LED
- **Button mode**: hold (continuous) or single-press (one-shot)
- **Steps**: ordered list of step definitions

Each step consists of:
- **Valve states**: bitmask or per-valve on/off for all 8 valves
- **Igniter state**: on/off
- **Igniter timing offset**: delay relative to valve activation
- **Transition condition**: what triggers advancement to the next step
  - Timed (fixed ms duration)
  - Button release
  - Pressure threshold (specific PSI value, above or below)
  - Pressure-adaptive (feedback-driven timing adjustment)
  - Loop to step N
  - End

---

## Example Macros

### "Flame Thrower → Fireball"
Single accumulator sustained flame, then 3-accumulator fireball on release.
1. **Step 1** — Close isolation valves 2, 3, 4 (NO energized). Open poof valve 1 (NC energized). Igniter on. Transition: button release.
2. **Step 2** — Open poof valves 2, 3, 4 (NC energized). Deactivate isolation 2, 3, 4 (NO de-energized). Timed duration (experimentally determined). Transition: timed.
3. **Step 3** — All valves off. End.

### "Ping Pong"
Alternating half-fireballs between two accumulator pairs for rapid sustained fire.
1. **Step 1** — NC 1, 2 + NO 1, 2 activate. Igniter on. Timed duration (TBD). Transition: timed.
2. **Step 2** — NC 1, 2 + NO 1, 2 deactivate. NC 3, 4 + NO 3, 4 activate. Timed duration (TBD). Transition: timed.
3. **Step 3** — Loop to Step 1 (while button held). Transition: button release → End.

### "Pressure Adaptive Rotary"
Cycles through single-accumulator pops at a rate governed by pressure feedback.
1. **Step 1** — NO 2, 3, 4 activate (isolate). NC 1 activate. Igniter on. Timed duration (short pop). Transition: timed.
2. **Step 2** — NC 1 deactivate. NO 1 deactivate, NO 2, 3, 4 stay active → switch to NO 1, 3, 4 active. NC 2 activate. Pressure-adaptive delay. Transition: pressure recovery to threshold.
3. **Step 3** — Continue rotating through accumulators 3, 4, then loop. Transition: button release → End.

---

## MVP Scope

**Goal**: Fire the poofer reliably with the main button. Everything else comes later.

### MVP includes:
- Hardware abstraction module with all pin definitions
- RS-485 communication between control box and relay box
- Valve controller: main button fires all 8 valves while held, pressure lockout
- Input manager: main button press/release detection
- Display manager: show pressure and ready/locked status on LCD
- Battery monitor: read all 3 voltages, display warnings
- Config manager: basic settings file (pressure threshold)

### MVP does NOT include:
- Macro engine
- Menu system
- Aux button functionality
- LED patterns (static color only)
- Rotary encoder menu navigation
- Fuel gauge
- Igniter timing offsets (fires simultaneously with valves)

---

## Future Expansion Hooks

The following features are planned but not part of MVP. The modular architecture supports adding them without modifying existing modules:

- **Macro engine**: plugs into valve controller
- **Menu system**: uses display manager + input manager
- **RFID access control** (PN532): new module, ties into a system lock state
- **Temp/humidity/barometric sensor**: new module, data available to macro engine for combustion tuning
- **Servo-controlled venturi mixing valve**: new module, position configurable per macro step
- **WiFi/Bluetooth**: toggle on/off from menu, enables OTA updates
- **Music sync**: future input source that could drive macro timing
- **Fuel gauge**: tracks accumulator dump cycles via pressure sensor data

---

## Development Priority

1. Hardware abstraction + RS-485 comms (get the two boxes talking)
2. Valve controller + main button (fire the poofer)
3. Battery monitor + basic display (know your system status)
4. Config manager (persist pressure threshold across reboots)
5. Input manager with encoder (preparation for menus)
6. LED manager (button feedback)
7. Menu system (home screen, settings navigation)
8. Macro engine + aux button (the fun stuff)
9. Macro editor UI (create macros from the controller)
10. Future sensors, servo, WiFi, etc.
