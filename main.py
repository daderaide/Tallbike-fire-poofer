# main.py — Entry point for both boxes

from machine import Pin
import time

# Dev mode: hold aux button during boot to drop to REPL
aux = Pin(11, Pin.IN, Pin.PULL_UP)
time.sleep_ms(500)

if aux.value() == 0:
    print("DEV MODE")
    while True:
        time.sleep_ms(100)

import uasyncio as asyncio
from hardware import ROLE

async def relay_main():
    from comms import modbus
    from poof import process_commands, check_watchdog, update_comms_time

    while True:
        if modbus.process():
            update_comms_time()
        process_commands()
        check_watchdog()
        await asyncio.sleep_ms(0)

async def control_main():
    from comms import host, SLAVE_ADDR
    from hardware import main_btn
    from inputs import encoder_delta, encoder_clicked, aux_clicked
    from menu import Menu
    import time

    menu = Menu()

    connected = False
    last_status = None
    firing = False
    aux_macro_idx = 0  # 0 = none assigned

    cmd_queue = []

    def queue_cmd(priority, register, value):
        cmd_queue.append((priority, register, value))
        cmd_queue.sort(key=lambda x: x[0])

    async def handle_button():
        nonlocal firing
        while True:
            if main_btn.value() == 0 and not firing and connected:
                firing = True
                queue_cmd(0, 101, 1)

            elif main_btn.value() == 1 and firing:
                firing = False
                queue_cmd(0, 101, 0)

            await asyncio.sleep_ms(10)

    async def handle_leds():
        from leds import update, set_color, set_off
        last = time.ticks_ms()
        was_home = False
        while True:
            now = time.ticks_ms()
            delta = time.ticks_diff(now, last)
            last = now

            on_home = menu.active is menu.home
            if on_home and not was_home:
                # Returned to home screen — show macro color
                color = menu.home.aux_macro_color
                if color:
                    set_color(color[0], color[1], color[2])
                else:
                    set_off()
            elif not on_home and was_home:
                # Entered menus — LED off
                set_off()
            was_home = on_home

            update(delta)
            await asyncio.sleep_ms(30)

    async def handle_menu():
        nonlocal aux_macro_idx
        while True:
            d = encoder_delta()
            click = encoder_clicked()
            aux = aux_clicked()

            on_home = menu.active is menu.home

            if aux and on_home and aux_macro_idx > 0 and connected:
                # Fire aux macro
                queue_cmd(0, 102, aux_macro_idx)
            elif aux and on_home:
                # No macro assigned or not connected, ignore aux
                pass
            else:
                # Normal menu update (aux = back in menus)
                menu.update(d, click, aux)
                # Check if a macro was just assigned
                if menu.home.aux_macro_name != '(none)':
                    # Look up macro index
                    from macro_store import list_macros
                    names = sorted([n for n in list_macros() if n != 'main_poof'])
                    for i, name in enumerate(names):
                        from macro_store import load
                        m = load(name)
                        if m.get('name') == menu.home.aux_macro_name:
                            aux_macro_idx = i + 1  # 1-indexed
                            break
                else:
                    aux_macro_idx = 0
                continue

            # Still need to handle encoder even when aux fired macro
            menu.update(d, click, False)

            await asyncio.sleep_ms(20)

    async def comms_task():
        nonlocal connected, last_status
        arm_counter = 0

        while True:
            while cmd_queue:
                _, register, value = cmd_queue.pop(0)
                try:
                    host.write_single_register(
                        slave_addr=SLAVE_ADDR,
                        register_address=register,
                        register_value=value,
                        signed=False
                    )
                except:
                    pass

            try:
                status = host.read_holding_registers(
                    slave_addr=SLAVE_ADDR,
                    starting_addr=0,
                    register_qty=10,
                    signed=False
                )
                if not connected:
                    connected = True

                if status != last_status:
                    menu.home.update_status(
                        state=status[0],
                        error=status[8],
                        pressure=status[2],
                        batt_v=status[4]
                    )
                    last_status = status
            except:
                if connected:
                    connected = False
                    last_status = None
                    menu.home.set_disconnected()

                await asyncio.sleep_ms(500)
                continue

            arm_counter += 1
            if arm_counter >= 10 and connected:
                arm_counter = 0
                queue_cmd(2, 100, 1)

            await asyncio.sleep_ms(10)

    await asyncio.gather(handle_button(), comms_task(), handle_leds(), handle_menu())

try:
    if ROLE == 'relay':
        loop = asyncio.get_event_loop()
        loop.create_task(relay_main())
        loop.run_forever()
    elif ROLE == 'control':
        loop = asyncio.get_event_loop()
        loop.create_task(control_main())
        loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    asyncio.new_event_loop()