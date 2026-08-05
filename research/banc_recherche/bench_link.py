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

    def stroke(self, direction, speed=800, mm=None):
        """Course unique du soufflet (mesure) : +1 = pousser (pression +),
        −1 = tirer (aspiration). Une seule passe, sans auto-inversion — pour
        acquérir pendant une pression stable. `mm` : distance (défaut = course
        complète). Correspond aux deux sens de pression (l'ancien `P_pos`)."""
        d = 1 if direction >= 0 else -1
        cmd = f"STROKE {d} {speed}"
        if mm is not None:
            cmd += f" {mm}"
        return self.send(cmd)
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

    def collect_telem(self, duration_s: float) -> list[dict]:
        """Collecte les trames de télémétrie pendant `duration_s` (pour synchro
        avec un enregistrement audio simultané)."""
        frames = []
        t0 = time.time()
        while time.time() - t0 < duration_s:
            fr = self.telem(timeout=max(0.05, duration_s))
            if fr is not None:
                frames.append(fr)
        return frames

    @staticmethod
    def mean_pq(frames: list[dict]):
        """Moyenne pression `p` (Pa) et débit `q` sur des trames de télémétrie."""
        import numpy as np
        if not frames:
            return float("nan"), float("nan")
        p = np.array([f.get("p", np.nan) for f in frames], dtype="float64")
        q = np.array([f.get("q", np.nan) for f in frames], dtype="float64")
        return float(np.nanmean(p)), float(np.nanmean(q))
