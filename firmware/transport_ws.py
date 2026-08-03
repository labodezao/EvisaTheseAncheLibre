# Transport sans fil : WiFi + WebSocket (lien principal vers l'accordeur web).
# Nécessite `microdot` (mip.install("microdot"), + microdot.websocket).
# Optionnel : si microdot ou le WiFi manquent, le banc tourne sur l'UART seul.
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio
import config as C

try:
    import network
    from microdot import Microdot
    from microdot.websocket import with_websocket
    _HAS_WS = True
except ImportError:
    _HAS_WS = False


async def connect_wifi(disp=None, timeout_s=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(C.WIFI_SSID, C.WIFI_PASS)
        for _ in range(timeout_s * 5):
            if wlan.isconnected():
                break
            if disp:
                disp.message("WiFi...", C.WIFI_SSID)
            await asyncio.sleep_ms(200)
    return wlan.ifconfig()[0] if wlan.isconnected() else None


def make_app(bench):
    """Crée l'app microdot exposant /ws (commandes + télémétrie)."""
    app = Microdot()

    @app.route("/ws")
    @with_websocket
    async def ws(request, sock):
        bench.link = "WiFi"

        async def sender():
            while True:
                if bench.stream:
                    try:
                        await sock.send(bench.telem())
                    except Exception:
                        return
                await asyncio.sleep_ms(max(20, 1000 // max(1, bench.telem_hz)))

        st = asyncio.create_task(sender())
        try:
            while True:
                msg = await sock.receive()
                if msg is None:
                    break
                resp = bench.handle(msg if isinstance(msg, str) else msg.decode())
                if resp:
                    await sock.send(resp)
        finally:
            st.cancel()
            bench.link = "-"

    return app


async def start(bench):
    """Démarre le WiFi + serveur WebSocket si disponibles. Renvoie l'IP ou None."""
    if not _HAS_WS or not C.WIFI_SSID:
        return None
    ip = await connect_wifi(bench.display)
    if not ip:
        return None
    app = make_app(bench)
    asyncio.create_task(app.start_server(port=C.WS_PORT))
    return ip
