# MicroPython ESP32-S3 Project with Unit Tests

This project demonstrates a setup for writing MicroPython code for ESP32-S3 with unit tests that run on your development machine.

## Approach

- **Development**: Write code that will run on ESP32-S3 using MicroPython
- **Testing**: Run unit tests on your host machine using standard Python with mocks for hardware-specific modules
- **Structure**: Separate hardware abstractions from business logic for better testability

## Project Structure

```
pypoof/
├── src/              # MicroPython source code (runs on ESP32-S3)
│   ├── __init__.py
│   ├── hardware.py   # Hardware abstraction layer
│   └── app.py        # Your application logic
├── tests/            # Unit tests (runs on host Python)
│   ├── __init__.py
│   ├── test_app.py
│   └── mocks/        # Mock implementations of MicroPython modules
├── requirements.txt  # Python dependencies for testing
└── README.md
```

## Setup

**Recommended: Use a virtual environment** to keep dependencies isolated:

1. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate it
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run tests:
   ```bash
   pytest tests/
   # or
   python -m pytest tests/
   ```

**Note:** If you prefer to install globally (not recommended), you can skip the virtual environment step and just run `pip install -r requirements.txt` directly. However, using a venv prevents conflicts with other projects.

## IDE Support (Type Stubs)

To get proper autocomplete and type checking for MicroPython modules like `machine`, `network`, etc., we use **MicroPython type stubs**.

The `micropython-esp32-stubs` package is already included in `requirements.txt`. After installing dependencies, your IDE should automatically recognize MicroPython imports.

**For MyPy users**: The `mypy.ini` is configured to:
- Allow optional MicroPython imports (`machine`, `network`) that only exist on device
- Add type ignore comments for imports that fail on host Python (but work on ESP32-S3)
- Set appropriate paths for module discovery

**For VSCode/Pylance users**: The `.vscode/settings.json` and `pyrightconfig.json` are configured to use the stubs from your virtual environment.

If you still see import errors:
1. Make sure you've installed dependencies: `pip install -r requirements.txt`
2. Restart your IDE
3. Check that the stubs are installed: `pip list | grep micropython-esp32-stubs`

**Note**: The `type: ignore[import-untyped]` comments in `hardware.py` tell MyPy to ignore import errors for MicroPython modules that don't exist in standard Python. This is expected behavior since these modules only exist on the ESP32-S3.

## Testing Strategy

- **Mock hardware modules**: Create mock implementations of `machine`, `network`, etc.
- **Abstract hardware interactions**: Use wrapper classes that can be easily mocked
- **Test business logic**: Focus tests on your application logic, not hardware specifics
- **Hardware integration tests**: Run device-specific tests separately when needed

## Poofer Control Hardware Info

### Relay Box Specs

- **Relay and Valve Numbering:**

- **Relays 1-4**: Normally Closed Valves 1-4 (poof valves)
- **Relays 5-8**: Normally Open Valves 1-4 (isolation valves)

- **ADC model**: ADS1015
- **ADC I2C address**: `0x48` (address pin tied to ground)
- **A0**: pressure sensor
- **A1**: ignitor battery monitor (4.2V max)
- **A2**: valve battery monitor (12.6V through voltage divider = 3.737V, 0.2966 ratio)

- **Relay board model**: PCF8574A
- **Relay board I2C address**: `0x3F`

- **ESP32 board model**: ESP32-S3-DevKitC-1 v1.1
- **SDA**: GPIO1
- **SCL**: GPIO2

### UART (MAX485)

- **TX**: GPIO17 (UART1)
- **RX**: GPIO18 (UART1)
- **DE/RE**: GPIO8

### Main Control Box Specs

- **Display**: I2C LCD, address `0x27`
  - **SDA**: GPIO1
  - **SCL**: GPIO2

- **UART1 (MAX485)**
  - **TX**: GPIO17
  - **RX**: GPIO18
  - **DE/RE**: GPIO8

- **Rotary Encoder**
  - **CLK**: GPIO4
  - **DT**: GPIO5
  - **SW**: GPIO6 (internal pull-up)

- **Main Poofer Button**
  - **Button**: GPIO7 (internal pull-up)
  - **NeoPixel ring (16 LEDs)**: GPIO15

- **Aux Button**
  - **Button**: GPIO21 (internal pull-up)
  - **NeoPixel (1 LED)**: GPIO16

- **Battery Monitor**
  - **ADC**: GPIO9 (ADC1_CH8, through voltage divider, 4.2V max → 3.3V)

