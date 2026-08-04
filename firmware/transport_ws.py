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
        # File d'émission : le contrôleur diffuse (télémétrie ET rafales
        # d'acquisition) via bench._bcast → un writer qui empile ici ; une
        # tâche vide la file vers la socket. Ainsi le WebSocket reçoit la même
        # chose que l'UART (sinon les lignes 'A ...' d'ACQUIRE n'arrivaient pas).
        q = []

        def writer(s):
            q.append(s)
            if len(q) > 500:        # borne : on lâche le plus ancien
                del q[0]

        bench.add_writer(writer)
        bench.link = "WiFi"

        async def sender():
            while True:
                if q:
                    try:
                        await sock.send(q.pop(0))
                    except Exception:
                        return
                else:
                    await asyncio.sleep_ms(15)

        st = asyncio.create_task(sender())
        try:
            while True:
                msg = await sock.receive()
                if msg is None:
                    break
                resp = bench.handle(msg if isinstance(msg, str) else msg.decode())
                if resp:
                    q.append(resp + "\n")
        finally:
            st.cancel()
            try:
                bench._writers.remove(writer)
            except ValueError:
                pass
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
