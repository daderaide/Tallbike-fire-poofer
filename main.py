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
    from poof import init, process_commands, check_watchdog, update_comms_time, read_sensors

    init()

    while True:
        if modbus.process():
            update_comms_time()
        process_commands()
        read_sensors()
        check_watchdog()
        await asyncio.sleep_ms(0)

async def control_main():
    from comms import host, SLAVE_ADDR
    from hardware import main_btn
    from inputs import encoder_delta, encoder_clicked, aux_clicked
    from menu import Menu
    from leds import set_ring_pattern, set_ring_brightness, set_aux_brightness
    from display import lcd
    import settings
    import battery
    import time

    # Load persistent settings
    settings.load()
    set_ring_pattern(settings.get('ring_pattern'))
    set_ring_brightness(settings.get('ring_brightness'))
    set_aux_brightness(settings.get('aux_brightness'))
    if not settings.get('backlight'):
        lcd.no_backlight()

    # Init battery monitor (control box local ADC)
    battery.init()

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
        from hardware import aux_btn
        aux_firing = False
        RELEASE = 0xFFFF
        # _dbg_count = 0
        while True:
            try:
                on_home = menu.active is menu.home

                # Main button
                if main_btn.value() == 0 and not firing and not aux_firing and connected:
                    firing = True
                    # print('BTN: main press')
                    queue_cmd(0, 102, 0)
                elif main_btn.value() == 1 and firing:
                    firing = False
                    # print('BTN: main release')
                    queue_cmd(0, 102, RELEASE)

                # Aux button — only fires on home screen with a macro assigned
                if on_home and aux_macro_idx > 0 and connected:
                    if aux_btn.value() == 0 and not aux_firing and not firing:
                        aux_firing = True
                        # print('BTN: aux press idx={}'.format(aux_macro_idx))
                        queue_cmd(0, 102, aux_macro_idx)
                    elif aux_btn.value() == 1 and aux_firing:
                        aux_firing = False
                        # print('BTN: aux release')
                        queue_cmd(0, 102, RELEASE)
                elif aux_firing:
                    # print('BTN: aux emergency release on_home={} idx={} conn={}'.format(on_home, aux_macro_idx, connected))
                    aux_firing = False
                    queue_cmd(0, 102, RELEASE)

                # # Periodic state dump
                # _dbg_count += 1
                # if _dbg_count >= 500:  # every 5 seconds
                #     _dbg_count = 0
                #     if firing or aux_firing:
                #         print('BTN state: firing={} aux_firing={} on_home={} idx={} conn={}'.format(
                #             firing, aux_firing, on_home, aux_macro_idx, connected))

            except Exception as e:
                print('handle_button error:', e)
                firing = False
                aux_firing = False

            await asyncio.sleep_ms(10)

    async def handle_leds():
        from leds import update, set_aux_color, set_aux_off, set_aux_rainbow
        last = time.ticks_ms()
        last_color = None
        was_home = False
        while True:
            now = time.ticks_ms()
            delta = time.ticks_diff(now, last)
            last = now

            on_home = menu.active is menu.home
            if on_home:
                color = menu.home.aux_macro_color
                if color != last_color or not was_home:
                    last_color = color
                    if color == 'rainbow':
                        set_aux_rainbow()
                    elif color:
                        set_aux_color(color[0], color[1], color[2])
                    else:
                        set_aux_rainbow()  # default: rainbow when no macro
            elif not on_home and was_home:
                set_aux_off()
                last_color = None
            was_home = on_home

            update(delta)
            await asyncio.sleep_ms(30)

    async def handle_menu():
        nonlocal aux_macro_idx
        from macro_store import list_macros, load
        last_aux_name = menu.home.aux_macro_name

        while True:
            d = encoder_delta()
            click = encoder_clicked()
            aux = aux_clicked()

            on_home = menu.active is menu.home

            if aux and on_home:
                # Aux firing is handled by handle_button, consume the click
                # but still pass encoder input through
                menu.update(d, click, False)
            else:
                # Normal menu update (aux = back in menus)
                menu.update(d, click, aux)

            # Re-resolve macro index only when assignment changes
            cur_name = menu.home.aux_macro_name
            if cur_name != last_aux_name:
                last_aux_name = cur_name
                if cur_name != '(none)':
                    names = sorted([n for n in list_macros() if n != 'main_poof'])
                    aux_macro_idx = 0
                    for i, fname in enumerate(names):
                        m = load(fname)
                        if m.get('name') == cur_name:
                            aux_macro_idx = i + 1
                            break
                else:
                    aux_macro_idx = 0

            await asyncio.sleep_ms(20)

    async def comms_task():
        nonlocal connected, last_status
        from macro_sync import sync_pending, do_sync
        arm_counter = 0
        batt_counter = 0

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

            # Push macros to relay box if needed
            if connected and sync_pending():
                do_sync(host, SLAVE_ADDR)

            # Read control box battery periodically and push to relay
            batt_counter += 1
            if batt_counter >= 50:  # every ~500ms
                batt_counter = 0
                ctrl_mv = battery.read_control()
                if connected and ctrl_mv > 0:
                    queue_cmd(3, 6, ctrl_mv)  # low priority, reg 6

            try:
                status = host.read_holding_registers(
                    slave_addr=SLAVE_ADDR,
                    starting_addr=0,
                    register_qty=10,
                    signed=False
                )
                if not connected:
                    connected = True
                    # First connection — push all macros to relay box
                    from macro_sync import request_sync
                    request_sync()

                if status != last_status:
                    menu.home.update_status(
                        state=status[0],
                        error=status[8],
                        pressure=status[2],
                        batt_ign=status[4],
                        batt_valve=status[5],
                        batt_ctrl=battery.control_mv
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