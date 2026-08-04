# Point d'entrée du banc d'accordage (ESP32-S3, MicroPython).
# Démarre le contrôleur, les transports (UART + WiFi/WebSocket), le watchdog
# et un gestionnaire d'exceptions global — les défauts mettent les actionneurs
# en sécurité au lieu de figer le banc en silence (le bug de l'ancienne version).
import sys
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
from machine import WDT

import config as C
from bench import Bench
from transport_uart import UartTransport
import transport_ws

bench = None


def _exception_handler(loop, context):
    print("EXC:", context.get("message"))
    exc = context.get("exception")
    if exc:
        sys.print_exception(exc)
    if bench:
        try:
            bench.safe_stop()
            bench.display.message("FAUT", str(context.get("message"))[:16])
        except Exception:
            pass


async def _wdt_feeder(wdt):
    while True:
        wdt.feed()
        await asyncio.sleep_ms(C.WDT_MS // 3)


async def amain():
    global bench
    bench = Bench()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_exception_handler)

    # Transports : UART toujours actif (bring-up/pont), WiFi/WS si configuré.
    uart = UartTransport(bench, C.UART_ID, C.PIN_UART_TX, C.PIN_UART_RX, C.UART_BAUD)
    asyncio.create_task(uart.task())

    ip = await transport_ws.start(bench)
    if ip:
        bench.link = "WiFi"
        bench.display.message("Banc pret", "WiFi " + ip, "ws:%d" % C.WS_PORT)

    # Watchdog : redémarre le banc si la boucle se fige.
    asyncio.create_task(_wdt_feeder(WDT(timeout=C.WDT_MS)))

    await bench.run()          # homing + tare + démarre les tâches
    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(amain())
except KeyboardInterrupt:
    if bench:
        bench.safe_stop()
