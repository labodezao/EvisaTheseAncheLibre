"""Constantes du banc de recherche : audio, calibrations, grille DOE.

À adapter à ton installation (voies Behringer, échelles capteurs, géométrie).
"""
from dataclasses import dataclass, field


@dataclass
class AudioConfig:
    device: str | int | None = None     # None = périphérique par défaut ; sinon nom/index Behringer
    samplerate: int = 48000             # 48 kHz / 24 bits sur la Behringer
    blocksize: int = 1024
    in_channels: tuple[int, ...] = (0, 1, 2)   # stéréo micro/anche + mono (pression / réf EM)
    out_channels: tuple[int, ...] = (0,)       # sortie EM (OUTTA)
    # Étalonnage : Pa par unité pleine échelle sur la voie pression.
    pa_per_fs: float = 1000.0


@dataclass
class SweepConfig:
    f0: float = 50.0          # Hz début
    f1: float = 2000.0        # Hz fin
    duration: float = 5.0     # s
    amplitude: float = 0.3    # 0..1 pleine échelle sortie EM
    method: str = "log"       # "log" | "linear"


@dataclass
class DoeConfig:
    # Reprise de Mesures.py : grille Section × Pression × Clapet × Position.
    # Plages d'origine : section 4→12 mm, clapet 2→22°, RECORD_SECONDS = 3.
    sections_mm: tuple[float, ...] = (4.0, 8.0, 12.0)
    pressures_pa: tuple[float, ...] = (600.0, 900.0, 1200.0)
    clapets_deg: tuple[float, ...] = (2.0, 12.0, 22.0)
    positions: tuple[int, ...] = (0,)
    settle_s: float = 4.0
    acquire_s: float = 3.0


@dataclass
class BenchLinkConfig:
    # Lien vers le firmware ESP32-S3 pour la partie air (soufflet, vanne, section).
    transport: str = "serial"     # "serial" | "ws"
    port: str = "/dev/ttyACM0"    # série
    ws_url: str = "ws://192.168.1.42:8266/ws"
    baud: int = 115200


@dataclass
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    sweep: SweepConfig = field(default_factory=SweepConfig)
    doe: DoeConfig = field(default_factory=DoeConfig)
    link: BenchLinkConfig = field(default_factory=BenchLinkConfig)
    hdf5_path: str = "mesures.h5"
    csv_path: str = "plan_exp.csv"


DEFAULT = Config()
