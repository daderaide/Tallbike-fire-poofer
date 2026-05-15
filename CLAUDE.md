# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Do not take any action without first explaining what you plan to do and getting my approval.
Do not load skills unless I explicitly ask for them.
Do not run commands without asking first.
When I ask a question, answer the question. Do not start scanning files or running commands unless I ask you to. I am learning. I want you to be my tutor, not my Dad who is doing my school science fair project for me and not letting me help.
MicroPython doesn't support relative imports. Only use absolute imports in the library files.

## Project Overview

This is a MicroPython project targeting two ESP32-S3-DevKitC-1-N8R8 boards that control a tallbike fire poofer ("The FUPA — Fire Up Poof Again"). A handheld **control box** communicates with a remote **relay box** over RS-485, driving 8 solenoid valves (4 NC poof valves + 4 NO isolation valves), a propane pressure sensor, battery monitors, and an igniter.

Code in `src/` and `main.py` runs on the ESP32-S3 via MicroPython. Tests in `tests/` run on host Python with hardware mocked.

## Commands

```bash
# One-time setup
make setup        # creates venv and installs requirements.txt
source venv/bin/activate

# Run all tests
make test         # or: pytest tests/ -v

# Run a single test
pytest tests/test_app.py::TestApp::test_start_stop

# Cleanup
make clean
```

## Architecture

### Key constraint: MicroPython vs host Python

`src/hardware.py` detects the runtime with a top-level `try/import machine` guard and sets `MICROPYTHON = True/False`. Every hardware class branches on that flag so the same source runs on-device and in host tests without changes.

MicroPython **does not support relative imports** — all imports within `src/` must be absolute (e.g., `from hardware import LED`, not `from .hardware import LED`).

### File roles

| File | Runs on | Purpose |
|------|---------|---------|
| `main.py` | Device only | Entry point. Current content: LCD init + AS5047P SPI encoder reader with timer/loop/asyncio options. This will be replaced by the main application loop as modules are built. |
| `src/hardware.py` | Both | Hardware abstraction layer — **all GPIO/I2C/UART/ADC access goes here**. Pin assignments are defined here and nowhere else. |
| `src/app.py` | Both | Placeholder application logic class; will evolve into the top-level coordinator. |
| `lib/lcd_i2c/` | Device only | Vendored I2C LCD driver. |
| `tests/conftest.py` | Host | Adds `src/` to `sys.path` so tests can import from there directly. |

### Planned modules (not yet created)

The architecture doc (`ARCHITECTURE.md`) defines the full module set. Priority order:
1. `comms.py` — RS-485 UART protocol, DE/RE direction toggling, message framing
2. `valves.py` — valve state machine, pressure lockout, igniter timing
3. `battery.py` — ADC reads for 3 battery packs (1S control box local, 1S igniter + 3S valve via ADS1015 over RS-485)
4. `display.py` — 20×4 I2C LCD at `0x27`; throttles I2C writes
5. `inputs.py` — debounced quadrature encoder + 2 buttons
6. `leds.py` — WS2812 NeoPixel ring (16 LEDs, GPIO15) + aux LED (GPIO10)
7. `config.py` — JSON config on flash, default values, write-on-save (not continuous)
8. `menu.py`, `macros.py`, `wifi.py` — post-MVP

### Hardware pin quick-reference

**Control box (ESP32-S3)**
- I2C: SDA=13, SCL=14 → LCD at `0x27` (via TXS0108E level shifter)
- UART1: TX=17, RX=18 → MAX485 RS-485; DE/RE=GPIO8
- Encoder: CLK=6, DT=5, SW=4 (internal pull-up on SW only)
- Main button: GPIO7 (internal pull-up), NeoPixel ring=GPIO15
- Aux button: GPIO11 (internal pull-up), NeoPixel=GPIO10
- Battery ADC: GPIO9, ADC1_CH8, 11dB atten, voltage divider ratio 0.6726

**Relay box (ESP32-S3)**
- I2C: SDA=2, SCL=1 → PCF8574A relay board at `0x21` (active-low), ADS1015 at `0x48`
- UART1: TX=17, RX=18 → MAX485 RS-485; DE/RE=GPIO8
- Igniter relay: GPIO38 (active-high, init LOW)
- ADS1015 channels: A3=pressure sensor, A2=igniter battery (1S), A1=valve battery (3S, divider ratio 0.2966), A0=unused
- Relay board: active-low (`0b11110000` = relays 5–8 ON, i.e. NO isolation valves energized)

### Testing strategy

Tests run entirely on host Python. The `MICROPYTHON = False` branch in each hardware class provides in-memory state (no actual GPIO). Use `pytest-mock` / `mocker.patch.object` to inject custom return values when the default mock behavior isn't enough. Do not add new hardware dependencies to tests — keep them pure Python.
