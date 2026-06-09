"""
Ponto de entrada: integra display SPI, touch e Moonraker num loop asyncio.
"""
import asyncio
import logging
import signal
import sys
import traceback

from drivers.display import ST7796SDisplay
from drivers.touch   import XPT2046Touch
from core.moonraker  import MoonrakerClient, PrinterState
from ui.renderer     import render, BUTTON_REGIONS, BUTTON_ACTIONS

MOONRAKER_HOST = "localhost"
MOONRAKER_PORT = 7125

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


async def main():
    log.info("Iniciando display...")
    try:
        display = ST7796SDisplay()
        log.info("Display OK")
    except Exception as e:
        log.error("Falha no display: %s\n%s", e, traceback.format_exc())
        sys.exit(1)

    client  = MoonrakerClient(MOONRAKER_HOST, MOONRAKER_PORT)
    _dirty  = asyncio.Event()

    log.info("Iniciando touch...")
    try:
        touch = XPT2046Touch()
        log.info("Touch OK")
    except Exception as e:
        log.warning("Touch nao disponivel: %s", e)
        touch = None

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
        log.info("render_loop iniciado")
        try:
            display.display_image(render(client.state))
        except Exception as e:
            log.error("Erro no primeiro render: %s\n%s", e, traceback.format_exc())
        while True:
            await _dirty.wait()
            _dirty.clear()
            try:
                display.display_image(render(client.state))
            except Exception as e:
                log.error("Erro no render: %s", e)

    client.on_update(on_state_update)
    if touch:
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
        log.info("Shutdown por sinal")
    except Exception as e:
        log.error("Erro fatal nas tasks: %s\n%s", e, traceback.format_exc())
    finally:
        display.backlight(False)
        display.cleanup()
        if touch:
            touch.cleanup()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
