"""
Ponto de entrada: integra display SPI, touch e Moonraker num loop asyncio.
"""
import asyncio
import signal
import sys

from drivers.display import ST7796SDisplay
from drivers.touch   import XPT2046Touch
from core.moonraker  import MoonrakerClient, PrinterState
from ui.renderer     import render, BUTTON_REGIONS, BUTTON_ACTIONS

MOONRAKER_HOST = "localhost"
MOONRAKER_PORT = 7125

display = ST7796SDisplay()
touch   = XPT2046Touch()
client  = MoonrakerClient(MOONRAKER_HOST, MOONRAKER_PORT)
_dirty  = asyncio.Event()


def on_state_update(_state: PrinterState):
    _dirty.set()


def on_touch(x: int, y: int):
    for i, (x0, y0, x1, y1) in enumerate(BUTTON_REGIONS):
        if x0 <= x <= x1 and y0 <= y <= y1:
            action = getattr(client, BUTTON_ACTIONS[i], None)
            if action:
                action()
            break


async def render_loop():
    display.display_image(render(client.state))
    while True:
        await _dirty.wait()
        _dirty.clear()
        display.display_image(render(client.state))


async def main():
    client.on_update(on_state_update)
    touch.on_touch(on_touch)

    tasks = [
        asyncio.create_task(client.run(), name="moonraker"),
        asyncio.create_task(render_loop(), name="renderer"),
    ]

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: [t.cancel() for t in tasks])

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        display.backlight(False)
        display.cleanup()
        touch.cleanup()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
