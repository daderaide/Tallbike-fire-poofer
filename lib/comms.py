# comms.py — Modbus RTU communication layer

from hardware import ROLE
from umodbus.serial import ModbusRTU

SLAVE_ADDR = 1
UART_ID = 1
BAUDRATE = 115200
TX_PIN = 17
RX_PIN = 18
CTRL_PIN = 8

if ROLE == 'relay':
    modbus = ModbusRTU(
        addr=SLAVE_ADDR,
        baudrate=BAUDRATE,
        uart_id=UART_ID,
        pins=[TX_PIN, RX_PIN],
        ctrl_pin=CTRL_PIN
    )

    # Status registers (read by control box)
    modbus.add_hreg(0, value=0)    # system_state
    modbus.add_hreg(1, value=0)    # relay_bitmask
    modbus.add_hreg(2, value=0)    # pressure_raw
    modbus.add_hreg(3, value=0)    # igniter_state
    modbus.add_hreg(4, value=0)    # batt_igniter
    modbus.add_hreg(5, value=0)    # batt_valve
    modbus.add_hreg(6, value=0)    # batt_control
    modbus.add_hreg(7, value=0)    # heartbeat
    modbus.add_hreg(8, value=0)    # error_code
    modbus.add_hreg(9, value=0)    # active_macro

    # Command registers (written by control box)
    modbus.add_hreg(100, value=0)  # arm
    modbus.add_hreg(101, value=0)  # fire
    modbus.add_hreg(102, value=0)  # run_macro
    modbus.add_hreg(103, value=0)  # save_config

    # Config sync registers (written by control box)
    modbus.add_hreg(200, value=0)  # config_length
    modbus.add_hreg(201, value=0)  # config_offset
    for i in range(202, 232):       # config_data (30 registers)
        modbus.add_hreg(i, value=0)
    modbus.add_hreg(232, value=0)  # config_checksum

elif ROLE == 'control':
    from umodbus.serial import Serial as ModbusRTUMaster
    
    host = ModbusRTUMaster(
        baudrate=BAUDRATE,
        uart_id=UART_ID,
        pins=[TX_PIN, RX_PIN],
        ctrl_pin=CTRL_PIN
    )