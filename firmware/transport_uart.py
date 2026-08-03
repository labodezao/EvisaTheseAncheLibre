# Transport série sur UART matériel (bring-up, débogage, pont USB-UART).
# Laisse le REPL USB libre pour le développement. Protocole ligne : chaque
# ligne reçue est une commande, chaque ligne émise une réponse ou une trame
# de télémétrie JSON.
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
from machine import UART, Pin


class UartTransport:
    def __init__(self, bench, uart_id, tx, rx, baud=115200):
        self.bench = bench
        self.uart = UART(uart_id, baudrate=baud, tx=Pin(tx), rx=Pin(rx),
                         timeout=0, rxbuf=512, txbuf=512)
        self.buf = b""
        bench.add_writer(self.write)

    def write(self, s):
        try:
            self.uart.write(s)
        except Exception:
            pass

    async def task(self):
        while True:
            n = self.uart.any()
            if n:
                self.buf += self.uart.read(n)
                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    resp = self.bench.handle(line.decode().strip())
                    if resp:
                        self.write(resp + "\n")
            await asyncio.sleep_ms(10)
