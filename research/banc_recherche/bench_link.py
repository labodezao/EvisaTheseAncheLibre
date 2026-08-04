"""Lien vers le firmware ESP32-S3 pour la partie **air** (soufflet motorisé,
vanne, axes section/clapet). Même protocole texte que l'onglet « Banc » de
l'accordeur web ; ici en série (pyserial) ou WebSocket.

Le banc de recherche gère l'EM et l'acquisition haute résolution côté PC, mais
délègue la pneumatique au même firmware que le banc d'accordage.
"""
from __future__ import annotations

import json
import time

from .config import BenchLinkConfig

try:
    import serial          # pyserial
except Exception:
    serial = None


class BenchLink:
    def __init__(self, cfg: BenchLinkConfig):
        self.cfg = cfg
        self._ser = None

    def open(self):
        if self.cfg.transport == "serial":
            if serial is None:
                raise RuntimeError("pyserial indisponible")
            self._ser = serial.Serial(self.cfg.port, self.cfg.baud, timeout=1)
        else:
            raise NotImplementedError("WebSocket : à câbler (websocket-client)")
        return self

    def close(self):
        if self._ser:
            self._ser.close()
            self._ser = None

    def send(self, cmd: str) -> str:
        if not self._ser:
            raise RuntimeError("lien fermé")
        self._ser.write((cmd + "\n").encode())
        return self._ser.readline().decode(errors="replace").strip()

    # --- Commandes air (miroir du firmware) ---------------------------------
    def home(self):            return self.send("HOME")
    def tare(self):            return self.send("TARE")
    def section(self, mm):     return self.send(f"SECTION {mm}")
    def clap(self, deg):       return self.send(f"CLAP {deg}")
    def pressure(self, pa):    return self.send(f"PRESSURE {pa}")
    def bellows(self, sps):    return self.send(f"BELLOWS {sps}")
    def press_btn(self, ch, on): return self.send(f"PRESS {ch} {1 if on else 0}")
    def all_off(self):         return self.send("ALLOFF")
    def stop(self):            return self.send("STOP")

    def telem(self, timeout=2.0) -> dict | None:
        """Attend une trame de télémétrie JSON."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            line = self._ser.readline().decode(errors="replace").strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except ValueError:
                    pass
        return None
