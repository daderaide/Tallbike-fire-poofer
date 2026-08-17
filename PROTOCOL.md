# Poofer Communication Protocol

## Overview

Communication between the control box and relay box uses Modbus RTU over RS-485 at 115200 baud. The control box is the Modbus host (initiates all communication). The relay box is the Modbus client (address 1).

The relay box is the operational brain — it stores and executes macros, manages valve states, monitors sensors, and handles safety logic. The control box is a thin client that sends commands and displays status.

Both boxes store identical copies of the config file (JSON). Config changes are made on the control box and pushed to the relay box. The control box is always the source of truth for config.

## Modbus Client Address

- Relay box: address 1

## Baud Rate

- 115200, 8N1

## Status Registers (read by control box)

| Register | Name              | Type   | Description                              |
|----------|-------------------|--------|------------------------------------------|
| 0        | system_state      | uint16 | 0=idle, 1=armed, 2=firing, 3=error      |
| 1        | relay_bitmask     | uint16 | Current state of all 8 relays            |
| 2        | pressure_raw      | uint16 | Raw ADC pressure reading                 |
| 3        | igniter_state     | uint16 | 0=off, 1=on                             |
| 4        | batt_igniter      | uint16 | Igniter battery voltage (mV)             |
| 5        | batt_valve        | uint16 | Valve battery voltage (mV)               |
| 6        | batt_control      | uint16 | Control box battery voltage (mV)         |
| 7        | heartbeat         | uint16 | Increments each cycle, rolls over        |
| 8        | error_code        | uint16 | 0=none, see error table                  |
| 9        | active_macro      | uint16 | Index of currently running macro, 0=none |

## Command Registers (written by control box)

| Register | Name              | Type   | Description                              |
|----------|-------------------|--------|------------------------------------------|
| 100      | arm               | uint16 | 1=arm, 0=disarm                          |
| 101      | (unused)          | uint16 | Reserved                                 |
| 102      | fire_macro        | uint16 | Macro index=press, 0xFFFF=release        |
| 103      | save_config       | uint16 | 1=save triggered, resets to 0 when done  |

## Config Sync Registers (written by control box)

| Register | Name              | Type   | Description                              |
|----------|-------------------|--------|------------------------------------------|
| 200      | config_length     | uint16 | Total byte length of incoming config     |
| 201      | config_offset     | uint16 | Byte offset of current chunk             |
| 202-231  | config_data       | uint16 | 30 registers = 60 bytes per chunk        |
| 232      | config_checksum   | uint16 | CRC of complete config file              |

## Boot Sequence

1. Both boxes power up, read `role.txt`, initialize hardware
2. Control box attempts to establish Modbus link with relay box
3. If link established:
   a. Control box reads local config JSON
   b. Control box pushes config to relay box via config sync registers
   c. Relay box saves config, confirms via save_config register reset to 0
   d. Control box begins polling status registers
   e. Relay box main loop begins (idle state, monitoring sensors)
   f. System ready
4. If link not established:
   a. Control box displays "No relay box" on LCD
   b. Control box operates in standalone mode (menu, config editing)
   c. Relay box enters standby (all valves closed, monitoring sensors)
   d. Both boxes continue retrying connection

## Watchdog / Comms Timeout

The relay box increments the heartbeat register (register 7) each main loop cycle. The control box reads it on every poll. If two consecutive reads return the same value, the control box displays a comms warning on the LCD.

The relay box tracks the timestamp of the last Modbus request received from the control box. If no request is received within 500ms:

1. Any running macro is immediately stopped
2. All relays set to off (bitmask 0xFF)
3. Igniter set to off
4. System state set to error (register 0 = 3)
5. Error code set to comms timeout (register 8 = 1)

The relay box remains in this state until comms are restored and an arm command is received.

The control box does not have a safety-critical timeout — if it loses comms, it displays "Comms lost" on the LCD and continues retrying. It can still be used for config editing in standalone mode.

## Error Codes (register 8)

| Code | Name              | Description                                      |
|------|-------------------|--------------------------------------------------|
| 0    | none              | No error                                         |
| 1    | comms_timeout     | No Modbus request received within 500ms          |
| 2    | over_pressure     | Pressure reading exceeds configured threshold     |
| 3    | low_batt_igniter  | Igniter battery below configured threshold        |
| 4    | low_batt_valve    | Valve battery below configured threshold          |
| 5    | macro_error       | Invalid macro step or bad config data             |
| 6    | ign_cooldown      | Igniter cooldown active — step paused             |

### Future Error Codes (reserved)

| Code | Name              | Description                                      |
|------|-------------------|--------------------------------------------------|
| 10   | igniter_failure   | No spark detected (requires sense wire feedback)  |
| 11   | relay_failure     | No voltage after relay (requires sense wires)     |