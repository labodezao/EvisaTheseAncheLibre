"""Banc de recherche — **une seule** application graphique (PyQt6 + pyqtgraph).

Remplace la constellation d'anciens scripts séparés (`MesAnche`, `Mesures`,
`Data_analysis`, `enveloppepraat`, `mes_seuil_autoentretien`, `plotsmeasure`,
`valvecontrol`…) par une GUI unique à onglets, chaque onglet pilotant un module
de `banc_recherche`. La logique numérique vit dans les modules ; la GUI n'est
qu'un pilote (fenêtres, boutons, tracés).

Onglets :
  1. Connexion / air      → bench_link (soufflet, vanne, section, clapet)
  2. Excitation EM        → excitation (sweep, résonances, phase)
  3. Analyse anche        → analysis.praat_calcs (Tresp, formants, pitch)
  4. Impédance            → impedance (P/Q, P·Q)
  5. Seuil auto-entretien → seuil (rampe, hystérésis)
  6. Plan d'expériences   → doe (grille auto Section×Pression×Clapet)
  7. Campagnes            → campaigns (relecture HDF5/npy de la thèse)
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..config import DEFAULT, Config


# ---------------------------------------------------------------------------
# Exécution en tâche de fond : les analyses longues (batch, sweep, Praat) ne
# doivent pas figer la fenêtre. Un QThread générique porte une fonction de
# travail `work(emit_progress)` et émet progress / done / failed.
# ---------------------------------------------------------------------------
_WORKER_CLS = None


def _worker_class():
    global _WORKER_CLS
    if _WORKER_CLS is not None:
        return _WORKER_CLS
    from PyQt6 import QtCore

    class Worker(QtCore.QThread):
        progress = QtCore.pyqtSignal(int, int, str)
        done = QtCore.pyqtSignal(object)
        failed = QtCore.pyqtSignal(str)

        def __init__(self, work):
            super().__init__()
            self._work = work

        def run(self):
            try:
                result = self._work(lambda k, t, m: self.progress.emit(k, t, m))
                self.done.emit(result)
            except Exception as e:                       # remonte l'erreur à l'UI
                self.failed.emit(str(e))

    _WORKER_CLS = Worker
    return Worker


def _run_async(state, work, on_progress=None, on_done=None, on_failed=None):
    """Lance `work(emit_progress)` dans un thread ; câble les signaux à l'UI.

    Garde une référence dans `state['_workers']` pour éviter le ramassage.
    """
    w = _worker_class()(work)
    if on_progress:
        w.progress.connect(on_progress)
    state.setdefault("_workers", [])
    state["_workers"].append(w)

    def _cleanup(*_):
        try:
            state["_workers"].remove(w)
        except ValueError:
            pass

    if on_done:
        w.done.connect(on_done)
    if on_failed:
        w.failed.connect(on_failed)
    w.done.connect(_cleanup)
    w.failed.connect(_cleanup)
    w.start()
    return w


# ---------------------------------------------------------------------------
# Construction de la fenêtre (imports Qt différés : la CLI marche sans écran).
# ---------------------------------------------------------------------------
def _build(cfg: Config):
    from PyQt6 import QtWidgets

    try:
        import pyqtgraph as pg
    except Exception:
        pg = None

    def plot_widget(title=""):
        if pg is not None:
            w = pg.PlotWidget(title=title)
            w.showGrid(x=True, y=True, alpha=0.3)
            return w
        lbl = QtWidgets.QLabel(f"[{title}]\npyqtgraph absent — tracé indisponible")
        lbl.setAlignment(QtWidgets.QtCore.Qt.AlignmentFlag.AlignCenter if hasattr(QtWidgets, "QtCore") else 0)
        return lbl

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("Banc de recherche — anches libres")
    tabs = QtWidgets.QTabWidget()

    state = {"cfg": cfg, "link": None, "sound": None, "sr": None, "acq": None}

    tabs.addTab(_tab_air(state), "Connexion / air")
    tabs.addTab(_tab_excitation(state, plot_widget), "Excitation EM")
    tabs.addTab(_tab_analysis(state, plot_widget), "Analyse anche")
    tabs.addTab(_tab_impedance(state), "Impédance")
    tabs.addTab(_tab_transfer(state, plot_widget), "Impédance 2 micros")
    tabs.addTab(_tab_fourmic(state, plot_widget), "Transmission 4 micros")
    tabs.addTab(_tab_ringdown(state, plot_widget), "Ring-down Q")
    tabs.addTab(_tab_material(state), "Matériau E")
    tabs.addTab(_tab_leak(state, plot_widget), "Fuite")
    tabs.addTab(_tab_seuil(state, plot_widget), "Seuil auto-entretien")
    tabs.addTab(_tab_doe(state), "Plan d'expériences")
    tabs.addTab(_tab_campaigns(state), "Campagnes")
    tabs.addTab(_tab_doe_analysis(state), "Analyse DOE")
    tabs.addTab(_tab_bifurcation(state, plot_widget), "Bifurcation")
    tabs.addTab(_tab_coherence(state, plot_widget), "Résonance cohérente")
    tabs.addTab(_tab_profile(state, plot_widget), "Profil laser")
    tabs.addTab(_tab_phase(state, plot_widget), "Espace des phases")
    tabs.addTab(_tab_frf(state, plot_widget), "FRF (swept-sine)")
    tabs.addTab(_tab_model(state, plot_widget), "Modèle anche")
    tabs.addTab(_tab_sample_model(state, plot_widget), "Sample → modèle")
    tabs.addTab(_tab_physical_synth(state, plot_widget), "Synthèse physique")
    tabs.addTab(_tab_hybrid(state, plot_widget), "Instruments (hybride)")
    tabs.addTab(_tab_live(state, plot_widget), "Jouer (MIDI)")

    win.setCentralWidget(tabs)
    win.resize(1100, 720)
    return win


def _row(*widgets):
    from PyQt6 import QtWidgets
    w = QtWidgets.QWidget()
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    for x in widgets:
        lay.addWidget(x if not isinstance(x, str) else QtWidgets.QLabel(x))
    lay.addStretch(1)
    return w


# ---- 1. Air (bench_link) ---------------------------------------------------
def _tab_air(state):
    from PyQt6 import QtWidgets
    from ..bench_link import BenchLink

    page = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(page)
    port = QtWidgets.QLineEdit(state["cfg"].link.port)
    status = QtWidgets.QLabel("déconnecté")

    def connect():
        try:
            state["link"] = BenchLink(state["cfg"].link).open()
            status.setText("connecté : " + port.text())
        except Exception as e:
            status.setText("échec : " + str(e))

    def cmd(fn):
        return lambda: status.setText(fn() if state["link"] else "non connecté")

    btn_c = QtWidgets.QPushButton("Connecter"); btn_c.clicked.connect(connect)
    home = QtWidgets.QPushButton("Homing"); home.clicked.connect(cmd(lambda: state["link"].home()))
    tare = QtWidgets.QPushButton("Tare"); tare.clicked.connect(cmd(lambda: state["link"].tare()))
    stop = QtWidgets.QPushButton("STOP"); stop.clicked.connect(cmd(lambda: state["link"].stop()))

    press = QtWidgets.QSpinBox(); press.setRange(0, 4000); press.setValue(900)
    go_p = QtWidgets.QPushButton("Pression →")
    go_p.clicked.connect(cmd(lambda: state["link"].pressure(press.value())))

    lay.addWidget(_row("Port série", port, btn_c))
    lay.addWidget(status)
    lay.addWidget(_row(home, tare, stop))
    lay.addWidget(_row("Pression (Pa)", press, go_p))
    lay.addStretch(1)
    return page


# ---- 2. Excitation EM (excitation) -----------------------------------------
def _tab_excitation(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import excitation

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    f0 = QtWidgets.QDoubleSpinBox(); f0.setRange(1, 20000); f0.setValue(state["cfg"].sweep.f0)
    f1 = QtWidgets.QDoubleSpinBox(); f1.setRange(1, 20000); f1.setValue(state["cfg"].sweep.f1)
    dur = QtWidgets.QDoubleSpinBox(); dur.setRange(0.5, 60); dur.setValue(state["cfg"].sweep.duration)
    plot = plot_widget("Fonction de transfert |H| (résonances)")
    table = QtWidgets.QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["f (Hz)", "|H|", "phase (rad)"])
    status = QtWidgets.QLabel("")

    def run():
        sw = state["cfg"].sweep
        sw.f0, sw.f1, sw.duration = f0.value(), f1.value(), dur.value()
        btn.setEnabled(False); status.setText("balayage…")

        def work(emit):
            freqs, H = excitation.response(state["cfg"].audio, sw)
            return freqs, H, excitation.resonances(freqs, H)

        def on_done(res):
            btn.setEnabled(True)
            freqs, H, peaks = res
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(freqs, abs(H))
            table.setRowCount(len(peaks))
            for i, (fr, mag, ph) in enumerate(peaks):
                for j, v in enumerate((f"{fr:.1f}", f"{mag:.3g}", f"{ph:.2f}")):
                    table.setItem(i, j, QtWidgets.QTableWidgetItem(v))
            status.setText(f"{len(peaks)} résonances")

        def on_failed(msg):
            btn.setEnabled(True); status.setText("erreur : " + msg)

        _run_async(state, work, None, on_done, on_failed)

    btn = QtWidgets.QPushButton("Balayer (sweep)"); btn.clicked.connect(run)
    lay.addWidget(_row("f0", f0, "f1", f1, "durée", dur, btn))
    lay.addWidget(plot); lay.addWidget(table); lay.addWidget(status)
    return page


# ---- 3. Analyse anche (analysis.praat_calcs) -------------------------------
def _tab_analysis(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import analysis

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    info = QtWidgets.QLabel("Charger un WAV, ou utiliser la dernière acquisition.")
    plot = plot_widget("Enveloppe / pitch / intensité")
    results = QtWidgets.QLabel("—")

    def load_wav():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "Ouvrir un WAV", "", "WAV (*.wav)")
        if not fn:
            return
        try:
            from scipy.io.wavfile import read
            sr, data = read(fn)
            import numpy as np
            sig = data.astype("float64")
            if sig.ndim > 1:
                sig = sig[:, 0]
            state["sound"], state["sr"] = sig / (abs(sig).max() or 1), int(sr)
            info.setText(f"{fn}  ({sr} Hz, {len(sig)} éch.)")
        except Exception as e:
            info.setText("échec lecture : " + str(e))

    def run():
        if state["sound"] is None:
            results.setText("aucun son chargé"); return
        btn_r.setEnabled(False); results.setText("analyse Praat…")
        sig, sr = state["sound"], state["sr"]

        def work(emit):
            return analysis.praat_calcs(sig, sr)

        def on_done(r):
            btn_r.setEnabled(True)
            results.setText(
                f"Tresp = {r.tresp_s*1000:.1f} ms · F0 = {r.mean_fund_hz:.2f} Hz · "
                f"F1–F4 = {r.f1:.0f}/{r.f2:.0f}/{r.f3:.0f}/{r.f4:.0f} Hz · HNR = {r.hnr_db:.1f} dB")
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(r.env_t, r.env / (abs(r.env).max() or 1))

        def on_failed(msg):
            btn_r.setEnabled(True); results.setText("erreur : " + msg)

        _run_async(state, work, None, on_done, on_failed)

    btn_l = QtWidgets.QPushButton("Charger WAV"); btn_l.clicked.connect(load_wav)
    btn_r = QtWidgets.QPushButton("Analyser (Praat)"); btn_r.clicked.connect(run)
    lay.addWidget(_row(btn_l, btn_r)); lay.addWidget(info)
    lay.addWidget(plot); lay.addWidget(results)
    return page


# ---- 4. Impédance (impedance) ----------------------------------------------
def _tab_impedance(state):
    from PyQt6 import QtWidgets
    from .. import impedance
    import numpy as np

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    out = QtWidgets.QLabel("Charger un CSV pression/débit (colonnes p,q) ou une acquisition.")

    def load_csv():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "CSV p,q", "", "CSV (*.csv)")
        if not fn:
            return
        try:
            arr = np.genfromtxt(fn, delimiter=",", names=True)
            r = impedance.compute(arr["p"], arr["q"])
            out.setText(f"Z = P/Q = {r.impedance:.2f} · P·Q = {r.pui_hydro:.3g} · "
                        f"P̄ = {r.p_mean:.1f} Pa · Q̄ = {r.q_mean:.3f}")
        except Exception as e:
            out.setText("erreur : " + str(e))

    btn = QtWidgets.QPushButton("Charger CSV p,q"); btn.clicked.connect(load_csv)
    lay.addWidget(_row(btn)); lay.addWidget(out); lay.addStretch(1)
    return page


# ---- 5. Seuil auto-entretien (seuil) ---------------------------------------
def _tab_seuil(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import seuil
    import numpy as np

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    plot = plot_widget("Rampe pression ↔ amplitude (hystérésis)")
    out = QtWidgets.QLabel("Charger un CSV (colonnes pressure,amplitude) montée+descente.")

    def load_csv():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "CSV rampe", "", "CSV (*.csv)")
        if not fn:
            return
        try:
            arr = np.genfromtxt(fn, delimiter=",", names=True)
            p, a = arr["pressure"], arr["amplitude"]
            r = seuil.detect(p, a, amp_thresh=0.1 * np.nanmax(a))
            out.setText(f"P_on = {r.p_on:.0f} · P_off = {r.p_off:.0f} · "
                        f"hystérésis = {r.hysteresis:.0f} Pa")
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(p, a)
        except Exception as e:
            out.setText("erreur : " + str(e))

    btn = QtWidgets.QPushButton("Charger CSV rampe"); btn.clicked.connect(load_csv)
    lay.addWidget(_row(btn)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- 6. Plan d'expériences (doe) -------------------------------------------
def _tab_doe(state):
    from PyQt6 import QtWidgets
    from .. import doe

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    d = state["cfg"].doe
    sec = QtWidgets.QLineEdit(",".join(str(x) for x in d.sections_mm))
    pre = QtWidgets.QLineEdit(",".join(str(x) for x in d.pressures_pa))
    cla = QtWidgets.QLineEdit(",".join(str(x) for x in d.clapets_deg))
    stroke = QtWidgets.QCheckBox("Mode soufflet (course pousser/tirer)")
    stroke.setChecked(d.use_stroke)
    speeds = QtWidgets.QLineEdit(",".join(str(x) for x in d.stroke_speeds))
    prog = QtWidgets.QProgressBar()
    table = QtWidgets.QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(["#", "S", "P/sens", "Clap", "Tresp", "Z"])
    status = QtWidgets.QLabel("")

    def _sync_mode():
        # En mode soufflet, le champ « Pression » devient « Vitesse » (pas/s).
        pre.setEnabled(not stroke.isChecked())
        speeds.setEnabled(stroke.isChecked())
    stroke.toggled.connect(_sync_mode)

    def parse(le):
        return tuple(float(x) for x in le.text().split(",") if x.strip())

    def add_row(pt):
        r = table.rowCount(); table.insertRow(r)
        # En mode soufflet la colonne « P/sens » montre le sens (pousser/tirer).
        col2 = ("pousser" if pt.position == 0 else "tirer") if d.use_stroke else f"{pt.pressure_pa:.0f}"
        vals = (pt.idx, pt.section_mm, col2, pt.clapet_deg,
                f"{pt.tresp_ms:.1f}", f"{pt.impedance:.1f}")
        for j, v in enumerate(vals):
            table.setItem(r, j, QtWidgets.QTableWidgetItem(str(v)))

    def run():
        d.use_stroke = stroke.isChecked()
        d.sections_mm, d.clapets_deg = parse(sec), parse(cla)
        if d.use_stroke:
            d.stroke_speeds = parse(speeds)
            axis2 = len(d.stroke_speeds) * len(d.stroke_directions)
        else:
            d.pressures_pa = parse(pre)
            axis2 = len(d.pressures_pa) * len(d.positions)
        total = len(d.sections_mm) * len(d.clapets_deg) * axis2
        prog.setMaximum(total); table.setRowCount(0); btn.setEnabled(False)

        def work(emit):
            pts = []
            for pt in doe.run(state["cfg"], link=state["link"], progress=emit):
                pts.append(pt)
            return pts

        def on_prog(k, tot, msg):
            prog.setValue(k); status.setText(f"{k}/{tot} — {msg}")

        def on_done(pts):
            btn.setEnabled(True)
            for pt in pts:
                add_row(pt)
            status.setText(f"terminé ({len(pts)} points) → {state['cfg'].csv_path}")

        def on_failed(msg):
            btn.setEnabled(True); status.setText("erreur : " + msg)

        _run_async(state, work, on_prog, on_done, on_failed)

    btn = QtWidgets.QPushButton("Lancer le DOE"); btn.clicked.connect(run)
    _sync_mode()
    lay.addWidget(_row("Section", sec, "Pression", pre, "Vitesse", speeds, "Clapet", cla))
    lay.addWidget(_row(stroke, btn))
    lay.addWidget(prog); lay.addWidget(table); lay.addWidget(status)
    return page


# ---- 7. Campagnes (campaigns) ----------------------------------------------
def _tab_campaigns(state):
    from PyQt6 import QtWidgets
    from .. import campaigns, analysis, batch

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    info = QtWidgets.QLabel("Ouvrir un HDF5 de campagne (Mesures.py).")
    idx = QtWidgets.QLineEdit("0,0,0,0")   # Ppos,Section,Pression,Clapet
    out = QtWidgets.QLabel("—")
    prog = QtWidgets.QProgressBar()
    state["_camp"] = {"f": None, "path": None}

    def open_h5():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "HDF5", "", "HDF5 (*.hdf5 *.h5)")
        if not fn:
            return
        try:
            f, present = campaigns.open_campaign(fn)
            state["_camp"]["f"] = f
            state["_camp"]["path"] = fn
            info.setText(f"{fn} — datasets : {', '.join(present.keys())}")
        except Exception as e:
            info.setText("erreur : " + str(e))

    def batch_run():
        path = state["_camp"]["path"]
        if not path:
            out.setText("aucun HDF5 ouvert"); return
        b3.setEnabled(False)

        def work(emit):
            return batch.analyse_campaign(path, csv_path=state["cfg"].csv_path, progress=emit)

        def on_prog(k, tot, msg):
            prog.setMaximum(tot); prog.setValue(k); out.setText(f"{k}/{tot} — {msg}")

        def on_done(df):
            b3.setEnabled(True)
            out.setText(f"campagne analysée : {len(df)} points → {state['cfg'].csv_path}")

        def on_failed(msg):
            b3.setEnabled(True); out.setText("erreur : " + msg)

        _run_async(state, work, on_prog, on_done, on_failed)

    def analyse_point():
        f = state["_camp"]["f"]
        if f is None:
            out.setText("aucun HDF5 ouvert"); return
        try:
            p, s, pr, c = (int(x) for x in idx.text().split(","))
            sig = campaigns.acoustic_slice(f, p, s, pr, c)
            r = analysis.praat_calcs(sig, 48000)
            out.setText(f"point ({p},{s},{pr},{c}) : Tresp {r.tresp_s*1000:.1f} ms · "
                        f"F0 {r.mean_fund_hz:.2f} Hz")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Ouvrir HDF5"); b1.clicked.connect(open_h5)
    b2 = QtWidgets.QPushButton("Analyser le point"); b2.clicked.connect(analyse_point)
    b3 = QtWidgets.QPushButton("Analyser toute la campagne → CSV"); b3.clicked.connect(batch_run)
    lay.addWidget(_row(b1)); lay.addWidget(info)
    lay.addWidget(_row("Ppos,Sec,Pres,Clap", idx, b2)); lay.addWidget(out)
    lay.addWidget(_row(b3)); lay.addWidget(prog)
    lay.addStretch(1)
    return page


# ---- Espace des phases (accéléromètre → Position/Vitesse/Accélération) -----
def _tab_phase(state, plot_widget):
    from PyQt6 import QtWidgets
    import os
    from .. import phase_space as psx, plots

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    hp = QtWidgets.QDoubleSpinBox(); hp.setRange(0.1, 500); hp.setValue(20.0); hp.setSuffix(" Hz")
    plot = plot_widget("Portrait de phase (Position × Vitesse)")
    out = QtWidgets.QLabel("Charger un WAV d'accélération (accéléromètre).")
    stq = {"path": None}

    def run():
        r = _load_wav(page, channels=1)
        if r is None:
            return
        _, sr, (a,) = r; stq["path"] = r[0]
        try:
            ps = psx.from_acceleration(a, sr, hp_hz=hp.value())
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(ps.position, ps.velocity)
            out.setText(f"pos max {abs(ps.position).max():.3g} m · "
                        f"vit max {abs(ps.velocity).max():.3g} m/s")
            d = os.path.dirname(stq["path"]) or "."
            plots.phase_3d(ps).savefig(os.path.join(d, "phase_3d.png"), dpi=150)
            plots.phase_portrait(ps).savefig(os.path.join(d, "phase_portrait.png"), dpi=150)
            out.setText(out.text() + f"  · figures → {d}/phase_*.png")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b = QtWidgets.QPushButton("Charger accéléro WAV → phase"); b.clicked.connect(run)
    lay.addWidget(_row("Passe-haut", hp, b)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- FRF par balayage sinus synchronisé ------------------------------------
def _tab_frf(state, plot_widget):
    from PyQt6 import QtWidgets
    import os
    import numpy as np
    from scipy.io.wavfile import write as wavwrite, read as wavread
    from .. import frf, plots

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    f1 = QtWidgets.QDoubleSpinBox(); f1.setRange(1, 20000); f1.setValue(20)
    f2 = QtWidgets.QDoubleSpinBox(); f2.setRange(1, 20000); f2.setValue(5000)
    dur = QtWidgets.QDoubleSpinBox(); dur.setRange(0.5, 30); dur.setValue(3.0)
    sr = QtWidgets.QSpinBox(); sr.setRange(8000, 96000); sr.setValue(48000)
    plot = plot_widget("FRF |H| (dB)")
    out = QtWidgets.QLabel("Générer un balayage à émettre, puis analyser l'enregistrement.")
    stq = {"sweep": None}

    def gen():
        stq["sweep"] = frf.exponential_sweep(f1.value(), f2.value(), dur.value(), sr.value())
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(page, "Enregistrer le balayage", "sweep.wav", "WAV (*.wav)")
        if fn:
            wavwrite(fn, sr.value(), (stq["sweep"].x * 32767).astype("int16"))
            out.setText("balayage enregistré : " + fn)

    def analyse():
        if stq["sweep"] is None:
            stq["sweep"] = frf.exponential_sweep(f1.value(), f2.value(), dur.value(), sr.value())
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "Enregistrement", "", "WAV (*.wav)")
        if not fn:
            return
        try:
            _sr, data = wavread(fn)
            rec = data.astype("float64"); rec = rec[:, 0] if rec.ndim > 1 else rec
            ir, _ = frf.linear_ir(rec, stq["sweep"])
            f, H = frf.frf(ir, stq["sweep"].fs)
            res = frf.resonances(f, H)
            if hasattr(plot, "plot"):
                mag, _ = frf.bode(f, H); band = f <= f2.value()
                plot.clear(); plot.plot(f[band], mag[band])
            out.setText("résonances : " + ", ".join(f"{r:.0f}" for r in res) + " Hz")
            plots.bode_plot(f, H).savefig(os.path.join(os.path.dirname(fn) or ".", "frf_bode.png"), dpi=150)
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Générer balayage (WAV)"); b1.clicked.connect(gen)
    b2 = QtWidgets.QPushButton("Analyser enregistrement → FRF"); b2.clicked.connect(analyse)
    lay.addWidget(_row("f1", f1, "f2", f2, "durée", dur, "fs", sr))
    lay.addWidget(_row(b1, b2)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Modèle non linéaire anche-cavité --------------------------------------
def _tab_model(state, plot_widget):
    from PyQt6 import QtWidgets
    import os
    from .. import reed_model, modal, plots, phase_space as psx

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    qin = QtWidgets.QDoubleSpinBox(); qin.setDecimals(7); qin.setRange(0, 1e-2); qin.setValue(3e-5)
    dur = QtWidgets.QDoubleSpinBox(); dur.setRange(0.005, 1.0); dur.setValue(0.05)
    plot = plot_widget("Portrait de phase (modèle)")
    out = QtWidgets.QLabel("Simule le modèle anche+cavité (RK4) → portraits de phase.")

    def run():
        try:
            rm = reed_model.ReedModel(n_modes=2)
            freqs = modal.natural_frequencies_np(rm.sec, 2)
            res = rm.simulate(dur.value(), fs=max(20000.0, 8 * freqs[0]), q_in=qin.value())
            ps = psx.PhaseSpace(res.t, res.position, res.velocity, res.acceleration)
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(res.position, res.velocity)
            out.setText(f"fréquences propres : {freqs[0]:.0f}, {freqs[1]:.0f} Hz · "
                        f"pos max {abs(res.position).max():.3g} m")
            plots.phase_3d(ps).savefig("modele_phase_3d.png", dpi=150)
            plots.phase_portrait(ps).savefig("modele_phase_portrait.png", dpi=150)
            out.setText(out.text() + "  · figures → modele_phase_*.png")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b = QtWidgets.QPushButton("Simuler (RK4)"); b.clicked.connect(run)
    lay.addWidget(_row("Débit d'entrée (m³/s)", qin, "durée (s)", dur, b))
    lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Résonance cohérente (balayage multi-enregistrements) ------------------
def _tab_coherence(state, plot_widget):
    from PyQt6 import QtWidgets
    import os
    import numpy as np
    from scipy.io.wavfile import read
    from .. import stochastic as st, plots

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    levels = QtWidgets.QLineEdit()
    levels.setPlaceholderText("intensités de bruit, séparées par virgules (optionnel)")
    plot = plot_widget("Cohérence vs bruit")
    out = QtWidgets.QLabel("Charger plusieurs WAV (un par intensité de bruit, ordre croissant).")
    stq = {"files": []}

    def load():
        fns, _ = QtWidgets.QFileDialog.getOpenFileNames(page, "WAV (un par niveau)", "", "WAV (*.wav)")
        if fns:
            stq["files"] = sorted(fns)
            out.setText(f"{len(fns)} fichiers")

    def run():
        if len(stq["files"]) < 2:
            out.setText("au moins 2 WAV requis"); return
        try:
            series, sr = [], None
            for fn in stq["files"]:
                sr, data = read(fn)
                s = data.astype("float64")
                series.append(s[:, 0] if s.ndim > 1 else s)
            lv = levels.text().strip()
            noise = ([float(x) for x in lv.split(",")] if lv
                     else list(range(len(series))))
            cr = st.coherence_resonance(noise, series, float(sr))
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(cr.noise, cr.coherence)
            out.setText(f"optimum : bruit = {cr.optimal_noise:.3g} · "
                        f"cohérence max = {cr.max_coherence:.3g}")
            d = os.path.dirname(stq["files"][0]) or "."
            plots.coherence_resonance_plot(cr).savefig(os.path.join(d, "coherence_resonance.png"), dpi=150)
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Charger WAV (multi)"); b1.clicked.connect(load)
    b2 = QtWidgets.QPushButton("Analyser la cohérence"); b2.clicked.connect(run)
    lay.addWidget(_row(b1, b2)); lay.addWidget(_row("Niveaux", levels))
    lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Profil laser (balayage de forme d'anche) ------------------------------
def _tab_profile(state, plot_widget):
    from PyQt6 import QtWidgets
    import os
    import numpy as np
    from .. import profile as prof, plots

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    cal = QtWidgets.QDoubleSpinBox(); cal.setDecimals(6); cal.setRange(1e-6, 1e3); cal.setValue(1.0)
    plot = plot_widget("Profil d'anche (déflexion)")
    out = QtWidgets.QLabel("Depuis le banc (SCAN) ou un CSV (position,valeur).")

    def _show(pos, val, src):
        pr = prof.from_scan(pos, val, mm_per_unit=cal.value())
        if hasattr(plot, "plot"):
            plot.clear(); plot.plot(pr.position_mm, pr.deflection_mm)
        out.setText(f"déflexion max = {pr.max_deflection:.3g} mm · "
                    f"courbure max = {pr.max_curvature:.3g}/mm · RMS = {pr.rms_curvature:.3g}")
        d = os.path.dirname(src) if src else "."
        plots.profile_plot(pr).savefig(os.path.join(d or ".", "profil.png"), dpi=150)

    def from_csv():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "CSV position,valeur", "", "CSV (*.csv)")
        if not fn:
            return
        try:
            arr = np.genfromtxt(fn, delimiter=",", names=True)
            names = arr.dtype.names
            _show(arr[names[0]], arr[names[1]], fn)
        except Exception as e:
            out.setText("erreur : " + str(e))

    def from_bench():
        link = state.get("link")
        if link is None:
            out.setText("banc non connecté (onglet Connexion / air)"); return
        try:
            lines = link.scan(20.0, 0.2)
            pos, val = prof.parse_scan_lines(lines)
            if pos.size:
                _show(pos, val, None)
            else:
                out.setText("aucune donnée (capteur laser ?)")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Charger CSV"); b1.clicked.connect(from_csv)
    b2 = QtWidgets.QPushButton("Balayer au banc (SCAN)"); b2.clicked.connect(from_bench)
    lay.addWidget(_row("Étalonnage mm/unité", cal, b1, b2))
    lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Bifurcation / physique stochastique -----------------------------------
def _tab_bifurcation(state, plot_widget):
    from PyQt6 import QtWidgets
    import os
    import numpy as np
    from .. import bifurcation as bif, stochastic as st, plots

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    plot = plot_widget("Diagramme de bifurcation / potentiel")
    out = QtWidgets.QLabel("Diagramme : CSV (param,amp_up[,amp_down]). "
                           "Stochastique : WAV/CSV série temporelle.")
    st_data = {"path": None}

    def _savefig(fig, name):
        d = os.path.dirname(st_data["path"] or ".") or "."
        p = os.path.join(d, name); fig.savefig(p, dpi=150)
        out.setText(out.text() + f"  · figure → {p}")

    def diagram():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "CSV param,amp", "", "CSV (*.csv)")
        if not fn:
            return
        try:
            st_data["path"] = fn
            arr = np.genfromtxt(fn, delimiter=",", names=True)
            names = arr.dtype.names
            pu = arr[names[0]]; au = arr[names[1]]
            pd_ = ad = None
            if len(names) >= 4:
                pd_, ad = arr[names[2]], arr[names[3]]
            bd = bif.diagram(pu, au, pd_, ad)
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(pu, au)
            out.setText(f"μ_on={bd.mu_on:.3g} · μ_off={bd.mu_off:.3g} · "
                        f"hystérésis={bd.hysteresis:.3g} · {bd.kind} · "
                        f"seuil Hopf={bd.hopf.threshold:.3g}")
            _savefig(plots.bifurcation_diagram(bd), "bifurcation.png")
        except Exception as e:
            out.setText("erreur : " + str(e))

    def stochastic():
        r = _load_wav(page, channels=1) if True else None
        # accepte aussi un CSV à une colonne
        try:
            if r is None:
                return
            _, sr, (sig,) = r
            st_data["path"] = r[0]
            km = st.kramers_moyal(sig, 1.0 / sr, bins=25)
            xx, phi = st.potential_from_drift(km)
            mins = st.potential_minima(xx, phi)
            msg = (f"états stables (minima) : {len(mins)} → "
                   f"{'bistable (bifurcation)' if len(mins) >= 2 else 'monostable'}")
            if len(mins) >= 2:
                D = float(np.nanmedian(km.diffusion[np.isfinite(km.diffusion)]))
                rate = st.kramers_from_potential(xx, phi, D)
                if rate == rate and rate > 0:
                    msg += f" · taux d'échappement Kramers ≈ {rate:.3g}/s (τ≈{1/rate:.3g} s)"
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(xx, phi)
            out.setText(msg)
            _savefig(plots.drift_diffusion_plot(km), "kramers_moyal.png")
            _savefig(plots.potential_plot(xx, phi), "potentiel.png")
        except Exception as e:
            out.setText("erreur : " + str(e))

    def stuart_landau():
        r = _load_wav(page, channels=1)
        if r is None:
            return
        try:
            _, sr, (sig,) = r
            sl = st.stuart_landau_fit(sig, sr)
            out.setText(f"Stuart-Landau : μ={sl.mu:.3g} · f₀={sl.omega/(2*np.pi):.2f} Hz · "
                        f"Landau a={sl.a:.3g} (saturation), b={sl.b:.3g} "
                        f"(glissement de fréquence) · amplitude cycle limite≈{sl.r_limit:.3g}")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Diagramme (CSV rampe)"); b1.clicked.connect(diagram)
    b2 = QtWidgets.QPushButton("Kramers-Moyal / potentiel (WAV)"); b2.clicked.connect(stochastic)
    b3 = QtWidgets.QPushButton("Fit Stuart-Landau (WAV)"); b3.clicked.connect(stuart_landau)
    lay.addWidget(_row(b1, b2, b3)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Analyse DOE (façon Minitab) -------------------------------------------
def _tab_doe_analysis(state):
    from PyQt6 import QtWidgets
    import os

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    factors = QtWidgets.QLineEdit("S_plus,P_plus,i_Clap")
    response = QtWidgets.QLineEdit("Freq0")
    inter = QtWidgets.QCheckBox("interactions"); inter.setChecked(True)
    quad = QtWidgets.QCheckBox("termes quadratiques (surface de réponse)")
    goal = QtWidgets.QComboBox(); goal.addItems(["maximiser", "minimiser"])
    txt = QtWidgets.QPlainTextEdit(); txt.setReadOnly(True)
    txt.setStyleSheet("font-family: monospace;")
    info = QtWidgets.QLabel("Charger un plan_exp.csv (sortie du DOE / batch).")
    st = {"df": None, "res": None, "path": None}

    def load():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "plan_exp.csv", "", "CSV (*.csv)")
        if not fn:
            return
        try:
            import pandas as pd
            st["df"] = pd.read_csv(fn); st["path"] = fn
            info.setText(f"{fn} — colonnes : {', '.join(st['df'].columns)}")
        except Exception as e:
            info.setText("erreur : " + str(e))

    def analyse():
        if st["df"] is None:
            info.setText("aucun CSV"); return
        try:
            from .. import doe_analysis as da
            facs = [f.strip() for f in factors.text().split(",") if f.strip()]
            st["res"] = da.analyze(st["df"], response.text().strip(), facs,
                                   interactions=inter.isChecked(), quadratic=quad.isChecked())
            txt.setPlainText(da.summary(st["res"]))
        except Exception as e:
            txt.setPlainText("erreur : " + str(e))

    def _savefig(fig, name):
        d = os.path.dirname(st["path"] or ".") or "."
        p = os.path.join(d, name)
        fig.savefig(p, dpi=150); info.setText("figure → " + p)

    def plot_effects():
        if st["df"] is None:
            return
        from .. import plots
        facs = [f.strip() for f in factors.text().split(",") if f.strip()]
        _savefig(plots.main_effects_plot(st["df"], response.text().strip(), facs),
                 "doe_effets_principaux.png")

    def plot_pareto():
        if st["res"] is None:
            analyse()
        if st["res"] is not None:
            from .. import plots
            _savefig(plots.pareto_plot(st["res"]), "doe_pareto.png")

    def run_optim():
        if st["res"] is None:
            analyse()
        if st["res"] is None:
            return
        try:
            from ..doe_analysis import optimize as opt
            import numpy as np
            res, df = st["res"], st["df"]
            facs = res.factors
            bounds = {f: (float(df[f].min()), float(df[f].max())) for f in facs}
            y = df[response.text().strip()]
            g = opt.Goal(predict=res.predict, kind="max" if goal.currentIndex() == 0 else "min",
                         low=float(y.min()), high=float(y.max()))
            r = opt.optimize([g], bounds, grid=11)
            best = ", ".join(f"{k}={v:.3g}" for k, v in r.best.items())
            info.setText(f"Optimum ({goal.currentText()}) : {best} · D = {r.composite:.3f}")
        except Exception as e:
            info.setText("erreur : " + str(e))

    b_load = QtWidgets.QPushButton("Charger CSV"); b_load.clicked.connect(load)
    b_fit = QtWidgets.QPushButton("Ajuster le modèle"); b_fit.clicked.connect(analyse)
    b_eff = QtWidgets.QPushButton("Effets principaux"); b_eff.clicked.connect(plot_effects)
    b_par = QtWidgets.QPushButton("Pareto"); b_par.clicked.connect(plot_pareto)
    b_opt = QtWidgets.QPushButton("Optimiser"); b_opt.clicked.connect(run_optim)
    lay.addWidget(_row("Facteurs", factors, "Réponse", response))
    lay.addWidget(_row(inter, quad, b_load, b_fit))
    lay.addWidget(_row(b_eff, b_par, goal, b_opt))
    lay.addWidget(info); lay.addWidget(txt)
    return page


def _load_wav(page, channels=1):
    """Ouvre un WAV, renvoie (sr, list de voies float64 normalisées) ou None."""
    from PyQt6 import QtWidgets
    from scipy.io.wavfile import read
    import numpy as np
    fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "Ouvrir un WAV", "", "WAV (*.wav)")
    if not fn:
        return None
    sr, data = read(fn)
    data = data.astype("float64")
    if data.ndim == 1:
        data = data[:, None]
    chans = [data[:, min(i, data.shape[1] - 1)] for i in range(channels)]
    chans = [c / (abs(c).max() or 1) for c in chans]
    return fn, int(sr), chans


# ---- Impédance 2 microphones (transfer) ------------------------------------
def _tab_transfer(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import transfer

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    spacing = QtWidgets.QDoubleSpinBox(); spacing.setDecimals(4); spacing.setRange(0.001, 1); spacing.setValue(0.03)
    x1 = QtWidgets.QDoubleSpinBox(); x1.setDecimals(4); x1.setRange(0.001, 2); x1.setValue(0.10)
    plot = plot_widget("Absorption α(f)")
    out = QtWidgets.QLabel("Charger un WAV stéréo (micro1, micro2).")
    st = {"wav": None}

    def load():
        r = _load_wav(page, channels=2)
        if r:
            st["wav"] = r
            out.setText(f"{r[0]} ({r[1]} Hz)")

    def run():
        if not st["wav"]:
            out.setText("aucun WAV"); return
        _, sr, (m1, m2) = st["wav"]
        try:
            f, H, _ = transfer.estimate_H12(m1, m2, sr)
            R, Z, alpha = transfer.reflection_impedance(f, H, spacing.value(), x1.value())
            band = (f > 50) & (f < 4000)
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(f[band], alpha[band])
            import numpy as np
            out.setText(f"α moyen (50–4000 Hz) = {np.nanmean(alpha[band]):.3f}")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Charger WAV 2 voies"); b1.clicked.connect(load)
    b2 = QtWidgets.QPushButton("Calculer α / Z"); b2.clicked.connect(run)
    lay.addWidget(_row("Écart micros (m)", spacing, "Dist. micro1→éch. (m)", x1))
    lay.addWidget(_row(b1, b2)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Transmission 4 microphones (matrice de transfert) ---------------------
def _tab_fourmic(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import transfer

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    pos = QtWidgets.QLineEdit("-0.10,-0.07,0.07,0.10")   # x1,x2,x3,x4 (m)
    plot = plot_widget("Perte par transmission TL(f)")
    out = QtWidgets.QLabel("Charger un WAV 4 voies (micros 1-2 amont, 3-4 aval).")
    st = {"wav": None}

    def load():
        r = _load_wav(page, channels=4)
        if r:
            st["wav"] = r; out.setText(f"{r[0]} ({r[1]} Hz)")

    def run():
        if not st["wav"]:
            out.setText("aucun WAV"); return
        _, sr, chans = st["wav"]
        try:
            positions = tuple(float(x) for x in pos.text().split(","))
            freqs, A, B, C, D, tl, alpha = transfer.four_mic_analyze(
                chans[0], chans[1], chans[2], chans[3], positions, sr)
            band = (freqs > 50) & (freqs < 4000)
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(freqs[band], tl[band])
            import numpy as np
            out.setText(f"TL moyen (50–4000 Hz) = {np.nanmean(tl[band]):.1f} dB")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Charger WAV 4 voies"); b1.clicked.connect(load)
    b2 = QtWidgets.QPushButton("Calculer TL"); b2.clicked.connect(run)
    lay.addWidget(_row("Positions x1,x2,x3,x4 (m)", pos))
    lay.addWidget(_row(b1, b2)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Ring-down / facteur Q -------------------------------------------------
def _tab_ringdown(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import ringdown

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    plot = plot_widget("Enveloppe de décroissance")
    out = QtWidgets.QLabel("Charger un WAV de décroissance (anche excitée puis coupée).")
    st = {"wav": None}

    def load():
        r = _load_wav(page, channels=1)
        if r:
            st["wav"] = r; out.setText(f"{r[0]} ({r[1]} Hz)")

    def run():
        if not st["wav"]:
            out.setText("aucun WAV"); return
        _, sr, (sig,) = st["wav"]
        try:
            r = ringdown.estimate(sig, sr)
            out.setText(f"f₀ = {r.freq_hz:.2f} Hz · α = {r.alpha:.2f} /s · "
                        f"ζ = {r.zeta:.2e} · Q = {r.q:.0f}")
            if hasattr(plot, "plot"):
                import numpy as np
                env = ringdown.analytic_envelope(sig)
                plot.clear(); plot.plot(np.arange(env.size) / sr, env)
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Charger WAV"); b1.clicked.connect(load)
    b2 = QtWidgets.QPushButton("Estimer Q / amortissement"); b2.clicked.connect(run)
    lay.addWidget(_row(b1, b2)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Matériau : module d'Young ---------------------------------------------
def _tab_material(state):
    from PyQt6 import QtWidgets
    from .. import material

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    fn = QtWidgets.QDoubleSpinBox(); fn.setRange(1, 20000); fn.setValue(440); fn.setSuffix(" Hz")
    L = QtWidgets.QDoubleSpinBox(); L.setDecimals(4); L.setRange(0.001, 0.5); L.setValue(0.020); L.setSuffix(" m")
    th = QtWidgets.QDoubleSpinBox(); th.setDecimals(5); th.setRange(0.0001, 0.01); th.setValue(0.0005); th.setSuffix(" m")
    rho = QtWidgets.QDoubleSpinBox(); rho.setRange(100, 20000); rho.setValue(7850); rho.setSuffix(" kg/m³")
    mode = QtWidgets.QSpinBox(); mode.setRange(1, 4); mode.setValue(1)
    out = QtWidgets.QLabel("—")

    def run():
        try:
            E = material.youngs_modulus(fn.value(), L.value(), th.value(), rho.value(), mode.value())
            out.setText(f"E = {E/1e9:.1f} GPa")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b = QtWidgets.QPushButton("Calculer E"); b.clicked.connect(run)
    lay.addWidget(_row("f_n", fn, "mode", mode))
    lay.addWidget(_row("Longueur", L, "Épaisseur", th, "ρ", rho))
    lay.addWidget(_row(b)); lay.addWidget(out); lay.addStretch(1)
    return page


# ---- Fuite : décroissance de pression --------------------------------------
def _tab_leak(state, plot_widget):
    from PyQt6 import QtWidgets
    from .. import leak
    import numpy as np

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    plot = plot_widget("Décroissance de pression p(t)")
    vol = QtWidgets.QDoubleSpinBox(); vol.setDecimals(6); vol.setRange(0, 1); vol.setValue(0.0)
    out = QtWidgets.QLabel("Charger un CSV (colonnes t,p) — sortie LEAKTEST.")

    def load_csv():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "CSV t,p", "", "CSV (*.csv)")
        if not fn:
            return
        try:
            arr = np.genfromtxt(fn, delimiter=",", names=True)
            t, p = arr["t"], arr["p"]
            v = vol.value() or None
            r = leak.fit_decay(t, p, volume_m3=v)
            out.setText(f"τ = {r.tau:.1f} s · demi-vie {r.half_life:.1f} s"
                        + (f" · G = {r.conductance:.2e} m³/s" if v else ""))
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(t, p)
        except Exception as e:
            out.setText("erreur : " + str(e))

    b = QtWidgets.QPushButton("Charger CSV décroissance"); b.clicked.connect(load_csv)
    lay.addWidget(_row("Volume (m³, opt.)", vol, b)); lay.addWidget(plot); lay.addWidget(out)
    return page


# ---- Sample -> modèle physique (sample_extract + synth_export) -------------
def _tab_sample_model(state, plot_widget):
    """Importer un sample monophonique, en extraire les paramètres d'un modèle
    physique, exporter vers une cible embarquée (STM32 / Dream)."""
    from PyQt6 import QtWidgets
    import numpy as np
    from .. import sample_extract, synth_export

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    info = QtWidgets.QLabel("Charger un sample **monophonique** (une note tenue, un seul instrument).")
    plot = plot_widget("Enveloppes des partiels")
    out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)
    out.setPlaceholderText("Les paramètres extraits s'afficheront ici.")

    n_part = QtWidgets.QSpinBox(); n_part.setRange(1, 64); n_part.setValue(12)
    n_res = QtWidgets.QSpinBox(); n_res.setRange(1, 16); n_res.setValue(6)

    def load_sample():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            page, "Ouvrir un sample", "", "Audio (*.wav *.flac *.aiff *.aif *.mp3 *.m4a);;Tous (*)")
        if not fn:
            return
        try:
            sig, sr = _read_audio(fn)
            state["sample"], state["sample_sr"] = sig, sr
            state["sample_name"] = Path(fn).stem
            info.setText(f"{fn}\n{sr} Hz · {len(sig)} éch. · {len(sig)/sr:.2f} s · mono")
        except Exception as e:
            info.setText("échec lecture : " + str(e))

    def run():
        if state.get("sample") is None:
            out.setPlainText("aucun sample chargé"); return
        btn_run.setEnabled(False); out.setPlainText("extraction…")
        sig, sr = state["sample"], state["sample_sr"]
        name = state.get("sample_name", "voice")
        npar, nres = n_part.value(), n_res.value()

        def work(emit):
            m = sample_extract.extract(sig, sr, name=name, n_partials=npar, n_resonators=nres)
            amps, times = (sample_extract.partial_envelopes(sig, sr, m.f0_hz, n_partials=npar)
                           if np.isfinite(m.f0_hz) else (None, None))
            return m, amps, times

        def on_done(res):
            m, amps, times = res
            btn_run.setEnabled(True)
            state["model"] = m
            out.setPlainText(_format_model(m))
            if hasattr(plot, "plot") and amps is not None:
                plot.clear()
                for k in range(min(amps.shape[0], 8)):
                    peak = amps[k].max() or 1.0
                    plot.plot(times, amps[k] / peak, pen=(k, 8))

        def on_failed(msg):
            btn_run.setEnabled(True); out.setPlainText("erreur : " + msg)

        _run_async(state, work, None, on_done, on_failed)

    def export(kind):
        m = state.get("model")
        if m is None:
            out.setPlainText("lance d'abord l'extraction"); return
        filt = {"json": "JSON (*.json)", "c": "En-tête C (*.h)", "wt": "En-tête C (*.h)"}[kind]
        default = {"json": f"{m.name}.json", "c": f"{m.name}.h", "wt": f"{m.name}_wavetable.h"}[kind]
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(page, "Exporter", default, filt)
        if not fn:
            return
        try:
            if kind == "json":
                synth_export.to_json(m, fn)
            elif kind == "c":
                synth_export.to_c_header(m, fn, fixed_point=True)
            else:
                synth_export.wavetable_to_c(synth_export.to_wavetable(m), m.name, fn)
            out.appendPlainText(f"\n→ écrit : {fn}")
        except Exception as e:
            out.appendPlainText(f"\nerreur export : {e}")

    btn_load = QtWidgets.QPushButton("Charger un sample"); btn_load.clicked.connect(load_sample)
    btn_run = QtWidgets.QPushButton("Extraire le modèle"); btn_run.clicked.connect(run)
    btn_json = QtWidgets.QPushButton("Export JSON"); btn_json.clicked.connect(lambda: export("json"))
    btn_c = QtWidgets.QPushButton("Export .h (STM32)"); btn_c.clicked.connect(lambda: export("c"))
    btn_wt = QtWidgets.QPushButton("Export wavetable .h"); btn_wt.clicked.connect(lambda: export("wt"))

    lay.addWidget(_row(btn_load, "Partiels", n_part, "Résonances", n_res, btn_run))
    lay.addWidget(info)
    lay.addWidget(plot)
    lay.addWidget(out)
    lay.addWidget(_row(btn_json, btn_c, btn_wt))
    return page


def _read_audio(path):
    """Lit un fichier audio en mono float64. WAV via scipy ; autres formats via
    `soundfile`/`librosa` s'ils sont installés (extra « musique »)."""
    import numpy as np
    p = str(path)
    if p.lower().endswith(".wav"):
        from scipy.io.wavfile import read
        sr, data = read(p)
        sig = data.astype("float64")
        if np.issubdtype(data.dtype, np.integer):
            sig /= float(np.iinfo(data.dtype).max)
    else:
        try:
            import soundfile as sf
            sig, sr = sf.read(p, dtype="float64", always_2d=False)
        except Exception:
            import librosa
            sig, sr = librosa.load(p, sr=None, mono=True)
            sig = np.asarray(sig, dtype="float64")
    sig = np.asarray(sig, dtype="float64")
    if sig.ndim > 1:
        sig = sig.mean(axis=1)
    return sig, int(sr)


def _format_model(m):
    """Résumé lisible d'un `SampleModel`."""
    import numpy as np
    L = [f"Sample « {m.name} » — {m.samplerate} Hz, {m.duration_s:.2f} s", ""]
    if not np.isfinite(m.f0_hz):
        L.append("Aucune hauteur franche détectée : sample non monophonique,")
        L.append("trop bruité, ou trop court. Rien n'est extrapolé.")
        return "\n".join(L)

    L.append(f"Hauteur      f0 = {m.f0_hz:.2f} Hz")
    if np.isfinite(m.vibrato_rate_hz):
        L.append(f"Vibrato      {m.vibrato_rate_hz:.2f} Hz, {m.vibrato_depth_cents:.1f} cents crête")
    L.append(f"Source       pente {m.source_slope_db_per_oct:+.2f} dB/octave de rang")
    L.append(f"Bruit        {m.percussive_pct:.1f} % (harmonique {m.harmonic_pct:.1f} %)")
    L.append(f"Dynamique    {m.brightness_slope_hz_per_db:+.1f} Hz de centroïde par dB")
    L.append("")
    L.append("Partiels (niveau dB / attaque s / inharmonicité cents) :")
    for k, lvl in enumerate(m.partial_levels_db):
        att = m.partial_attack_s[k] if k < len(m.partial_attack_s) else float("nan")
        inh = m.inharmonicity_cents[k] if k < len(m.inharmonicity_cents) else float("nan")
        L.append(f"  n={k+1:2d}   {lvl:+7.1f}   {att:6.3f}   {inh:+7.1f}")
    L.append("")
    L.append("Résonateur (biquads à générer) :")
    for r in m.resonators:
        L.append(f"  {r['freq_hz']:8.0f} Hz   Q={r['q']:5.1f}   {r['gain_db']:+6.1f} dB")
    if m.adsr:
        L.append("")
        L.append(f"ADSR (repli)  A={m.adsr['attack_s']:.3f}s  D={m.adsr['decay_s']:.3f}s  "
                 f"S={m.adsr['sustain_level']:.2f}  R={m.adsr['release_s']:.3f}s")
    return "\n".join(L)


# ---- Synthèse par modèle physique (calibrate + reed_oscillator) ------------
def _tab_physical_synth(state, plot_widget):
    """Injecter des sons, en tirer une anche, et faire sonner le modèle.

    Le sample sert de **mesure** : on en extrait la hauteur, on cale une
    languette dont la *fréquence de jeu* vaut celle du sample (le ressort
    d'air décale la note — surtout dans le grave), puis on fait osciller le
    modèle physique et on compare les spectres.
    """
    from PyQt6 import QtWidgets
    import numpy as np
    from .. import calibrate, sample_extract

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    info = QtWidgets.QLabel("Charge un ou plusieurs sons (une note tenue par fichier).")
    info.setWordWrap(True)
    plot = plot_widget("Spectre — original vs modèle")
    out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)

    drive = QtWidgets.QDoubleSpinBox()
    drive.setRange(1.05, 10.0); drive.setSingleStep(0.25); drive.setValue(2.0)
    drive.setToolTip("Nuance : multiple du seuil de démarrage (1,0 = au seuil, rien ne sort)")
    dur = QtWidgets.QDoubleSpinBox()
    dur.setRange(0.2, 10.0); dur.setSingleStep(0.5); dur.setValue(1.5); dur.setSuffix(" s")
    cal_box = QtWidgets.QCheckBox("caler sur la fréquence de jeu")
    cal_box.setChecked(True)
    cal_box.setToolTip("Inverse le décalage dû au ressort d'air (lent, utile surtout dans le grave)")

    def load():
        fns, _ = QtWidgets.QFileDialog.getOpenFileNames(
            page, "Sons à injecter", "", "Audio (*.wav *.flac *.aiff *.aif);;Tous (*)")
        if not fns:
            return
        items = []
        for fn in fns:
            try:
                sig, sr = _read_audio(fn)
                items.append((Path(fn).stem, sig, sr))
            except Exception as e:
                out.appendPlainText(f"échec lecture {fn} : {e}")
        if items:
            state["synth_samples"] = items
            info.setText(f"{len(items)} son(s) : " + ", ".join(n for n, _, _ in items))

    def run():
        items = state.get("synth_samples")
        if not items:
            out.setPlainText("aucun son chargé"); return
        btn_run.setEnabled(False); out.setPlainText("extraction, calage, synthèse…")
        d, dr, do_cal = dur.value(), drive.value(), cal_box.isChecked()

        def work(emit):
            res = []
            for name, sig, sr in items:
                m = sample_extract.extract(sig, sr, name=name, n_partials=12)
                if not np.isfinite(m.f0_hz):
                    res.append((name, None, None, None, None, "pas de hauteur franche"))
                    continue
                try:
                    if do_cal:
                        model, f_play, f_mode = calibrate.tune_to_playing_frequency(
                            m.f0_hz, n_iter=5, n_scan=14)
                    else:
                        model = calibrate.build_model(m.f0_hz)
                        f_mode = m.f0_hz
                        f_play = calibrate.playing_frequency(model, n_scan=14)
                    audio, nfo = calibrate.synthesize(model, dur=d, fs=sr, drive=dr)
                    dist = calibrate.compare_to_sample(audio, sig[:audio.size], sr)
                    res.append((name, m, audio, sr, dict(nfo, f_play=f_play,
                                                         f_mode=f_mode, dist=dist), None))
                except Exception as e:
                    res.append((name, m, None, None, None, str(e)))
            return res

        def on_done(res):
            btn_run.setEnabled(True)
            state["synth_out"] = [(n, a, sr) for n, _, a, sr, _, _ in res if a is not None]
            txt = []
            for name, m, audio, sr, nfo, err in res:
                if err:
                    txt.append(f"— {name} : {err}"); continue
                txt.append(
                    f"— {name}\n"
                    f"   sample f0 = {m.f0_hz:.1f} Hz\n"
                    f"   languette calée à {nfo['f_mode']:.1f} Hz -> joue {nfo['f_play']:.1f} Hz\n"
                    f"   seuil : {nfo['p_on']:.1f} Pa   nuance ×{nfo['drive']:.2f}\n"
                    f"   excursion {nfo['excursion_mm']:.3f} mm   "
                    f"pression {nfo['pressure_pa']:.0f} Pa   "
                    f"fente fermée {100*nfo['closed_fraction']:.0f} % du temps\n"
                    f"   écart spectral au sample : {nfo['dist']:.2f} dB "
                    f"({'très proche' if nfo['dist']<3 else 'même couleur' if nfo['dist']<8 else 'timbre différent'})")
            out.setPlainText("\n".join(txt) if txt else "rien à afficher")

            first = next(((n, m, a, sr) for n, m, a, sr, _, e in res if a is not None), None)
            if first and hasattr(plot, "plot"):
                name, m, audio, sr = first
                orig = next(s for nm, s, _ in items if nm == name)
                plot.clear()
                for sig, pen in ((orig[:audio.size], (0, 2)), (audio, (1, 2))):
                    sp = np.abs(np.fft.rfft(sig * np.hanning(sig.size)))
                    fr = np.fft.rfftfreq(sig.size, 1.0 / sr)
                    k = fr < 5000
                    ref = sp.max() or 1.0
                    plot.plot(fr[k], 20 * np.log10(np.maximum(sp[k], ref * 1e-6) / ref), pen=pen)

        def on_failed(msg):
            btn_run.setEnabled(True); out.setPlainText("erreur : " + msg)

        _run_async(state, work, None, on_done, on_failed)

    def export():
        outs = state.get("synth_out")
        if not outs:
            out.appendPlainText("\nrien à exporter : lance d'abord la synthèse"); return
        d = QtWidgets.QFileDialog.getExistingDirectory(page, "Dossier d'export")
        if not d:
            return
        from scipy.io.wavfile import write
        import numpy as np
        for name, audio, sr in outs:
            p = Path(d) / f"{name}_modele.wav"
            write(str(p), int(sr), (np.clip(audio, -1, 1) * 32767).astype("int16"))
            out.appendPlainText(f"→ {p}")

    btn_load = QtWidgets.QPushButton("Charger des sons"); btn_load.clicked.connect(load)
    btn_run = QtWidgets.QPushButton("Synthétiser"); btn_run.clicked.connect(run)
    btn_exp = QtWidgets.QPushButton("Exporter les WAV"); btn_exp.clicked.connect(export)

    lay.addWidget(_row(btn_load, "Nuance", drive, "Durée", dur, cal_box, btn_run))
    lay.addWidget(info)
    lay.addWidget(plot)
    lay.addWidget(out)
    lay.addWidget(_row(btn_exp))
    return page


def _tab_hybrid(state, plot_widget):
    """Tous les instruments à excitateur non linéaire, et l'export vers STM32.

    Trois gestes, dans cet ordre :

    1. **choisir une famille** — le son ne dira pas s'il vient d'une anche ou
       d'un archet, c'est l'a priori qu'on assume ;
    2. **injecter un son** (facultatif) — il donne la hauteur, la conicité de
       la perce, la position d'archet, la nuance. Sans son, on part du
       préréglage d'instrument ;
    3. **exporter le C** — moteur + table de paramètres, à compiler sur la
       carte. Le même modèle, sans ordinateur.

    Le rapport sépare toujours **ce qui a été mesuré** de **ce qui a été
    supposé**. Un paramètre supposé qu'on prend pour mesuré est la façon la
    plus sûre de se tromper longtemps.
    """
    from PyQt6 import QtWidgets
    import numpy as np
    from .. import hybrid, identify as idf, embedded as emb

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    plot = plot_widget("Spectre — son injecté vs modèle")
    out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)
    info = QtWidgets.QLabel("Aucun son : le modèle partira du préréglage d'instrument.")
    info.setWordWrap(True)

    instrument = QtWidgets.QComboBox()
    instrument.addItems(sorted(hybrid.INSTRUMENTS))
    instrument.setCurrentText('clarinette')

    note = QtWidgets.QDoubleSpinBox()
    note.setRange(40.0, 2000.0); note.setValue(147.0); note.setSuffix(" Hz")
    note.setToolTip("Hauteur visée (ignorée si un son est injecté)")

    dur = QtWidgets.QDoubleSpinBox()
    dur.setRange(0.2, 5.0); dur.setValue(1.0); dur.setSuffix(" s")

    srate = QtWidgets.QComboBox(); srate.addItems(["48000", "44100", "96000"])

    def load():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            page, "Son à identifier (une note tenue)", "",
            "Audio (*.wav *.flac *.aiff *.aif);;Tous (*)")
        if not fn:
            return
        try:
            sig, sr = _read_audio(fn)
        except Exception as e:
            out.appendPlainText(f"échec lecture : {e}"); return
        state["hybrid_sample"] = (Path(fn).stem, sig, sr)
        info.setText(f"son chargé : {Path(fn).stem} ({sig.size/sr:.2f} s, {sr:.0f} Hz)")

    def forget():
        state.pop("hybrid_sample", None)
        info.setText("Aucun son : le modèle partira du préréglage d'instrument.")

    def run():
        nom = instrument.currentText()
        sample = state.get("hybrid_sample")
        f_cible = note.value(); d = dur.value(); fs = float(srate.currentText())
        btn_run.setEnabled(False); out.setPlainText("identification et synthèse…")

        def work(emit):
            if sample:
                _, sig, sr = sample
                ident = idf.identify(sig, sr, nom)
            else:
                v = hybrid.build(nom, f_cible)
                ident = idf.Identification(
                    voice=v, instrument=nom, f0_hz=f_cible,
                    suppose={'tout': "préréglage d'instrument, aucun son injecté"})
                ex = v.exciter
                ident.level = (0.25 if isinstance(ex, hybrid.BowExciter)
                               else 2.9e-6 if isinstance(ex, hybrid.FreeReedExciter)
                               else 0.62 * ex.closing_pressure_pa)
            res = ident.voice.simulate(d, fs=fs, level=ident.level,
                                       oversample=8, settle=0.3)
            p = emb.params_from_voice(ident.voice, samplerate=fs, name=nom)
            return ident, res, p

        def on_done(r):
            btn_run.setEnabled(True)
            ident, res, p = r
            state["hybrid_params"] = p
            state["hybrid_audio"] = (ident.instrument, res.response, res.fs)

            f_joue = hybrid.playing_frequency(res.response, res.fs)
            niv = idf.harmonic_levels(res.response, res.fs, f_joue, 12)
            cpu = emb.cpu_estimate(p)
            unite = getattr(ident.voice.exciter, 'control_unit', '')
            txt = [ident.rapport(), "",
                   "— ce que le modèle produit —",
                   f"  hauteur jouée      : {f_joue:.2f} Hz",
                   f"  amplitude          : {np.ptp(res.response):.4g}",
                   f"  impairs − pairs    : {idf.odd_even_ratio(niv):+.1f} dB",
                   f"  pente spectrale    : {idf.spectral_decay(niv):+.1f} dB/octave",
                   "",
                   "— coût embarqué —",
                   f"  {cpu['biquads']} biquads · suréchantillonnage ×{p.oversample}"
                   f" · interne {p.fs_internal:.0f} Hz",
                   f"  {cpu['mflops_per_voice']:.1f} MFLOP/s par voix,"
                   f" état {cpu['state_bytes']} octets",
                   f"  ≈ {cpu['voices']:.0f} voix sur STM32H7 (480 MHz),"
                   f" {emb.cpu_estimate(p, 168.0)['voices']:.0f} sur F4 (168 MHz)",
                   f"  commande de jeu    : {ident.level:.4g} {unite}"]
            out.setPlainText("\n".join(txt))

            if hasattr(plot, "plot"):
                plot.clear()
                courbes = [(res.response, (1, 2))]
                if sample:
                    courbes.insert(0, (sample[1][:res.response.size], (0, 2)))
                for sig, pen in courbes:
                    sp = np.abs(np.fft.rfft(sig * np.hanning(sig.size)))
                    fr = np.fft.rfftfreq(sig.size, 1.0 / res.fs)
                    k = fr < 5000
                    ref = sp.max() or 1.0
                    plot.plot(fr[k], 20 * np.log10(np.maximum(sp[k], ref * 1e-6) / ref),
                              pen=pen)

        def on_failed(msg):
            btn_run.setEnabled(True); out.setPlainText("erreur : " + msg)

        _run_async(state, work, None, on_done, on_failed)

    def export_wav():
        a = state.get("hybrid_audio")
        if not a:
            out.appendPlainText("\nrien à exporter : lance d'abord la synthèse"); return
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(page, "Enregistrer le WAV",
                                                      f"{a[0]}.wav", "WAV (*.wav)")
        if not fn:
            return
        from scipy.io.wavfile import write
        import numpy as np
        sig = a[1] / (np.max(np.abs(a[1])) or 1.0)
        write(fn, int(a[2]), (np.clip(sig, -1, 1) * 32767).astype("int16"))
        out.appendPlainText(f"→ {fn}")

    def export_c():
        p = state.get("hybrid_params")
        if not p:
            out.appendPlainText("\nrien à exporter : lance d'abord la synthèse"); return
        d = QtWidgets.QFileDialog.getExistingDirectory(page, "Dossier pour le code C")
        if not d:
            return
        try:
            for f in emb.export_c(p, d):
                out.appendPlainText(f"→ {f}")
            out.appendPlainText(
                "\nÀ compiler tel quel :\n"
                "   gcc -std=c99 -O2 hybrid_voice.c ton_main.c -lm\n"
                "Sur cible : hv_reset(&st) une fois, puis hv_render() par bloc.\n"
                "Le moteur est le même pour tous les instruments — seule la "
                "table change.")
        except Exception as e:
            out.appendPlainText(f"échec export : {e}")

    btn_load = QtWidgets.QPushButton("Injecter un son"); btn_load.clicked.connect(load)
    btn_forget = QtWidgets.QPushButton("Oublier le son"); btn_forget.clicked.connect(forget)
    btn_run = QtWidgets.QPushButton("Identifier et synthétiser"); btn_run.clicked.connect(run)
    btn_wav = QtWidgets.QPushButton("Exporter le WAV"); btn_wav.clicked.connect(export_wav)
    btn_c = QtWidgets.QPushButton("Exporter le C (STM32)"); btn_c.clicked.connect(export_c)

    lay.addWidget(_row("Instrument", instrument, "Note", note, "Durée", dur,
                       "Sortie", srate, btn_run))
    lay.addWidget(_row(btn_load, btn_forget))
    lay.addWidget(info)
    lay.addWidget(plot)
    lay.addWidget(out)
    lay.addWidget(_row(btn_wav, btn_c))
    return page


def _tab_live(state, plot_widget):
    """Jouer le modèle physique au clavier MIDI, en direct.

    Le moteur est le **code C destiné au STM32**, compilé ici en bibliothèque
    partagée : ce qu'on entend est ce qui tournera sur la carte. Mesuré sur
    cette machine, 137 fois le temps réel à une voix et 26 fois à six.

    Chaque note est **accordée sur le moteur** avant de jouer : un modèle
    physique ne joue pas la fréquence qu'on lui dessine, et c'est la
    géométrie qu'on corrige, pas la sortie.

    Deux choses qu'un sampler ne fait pas, et qui sont tout l'intérêt :

    - **l'attaque n'est pas plaquée** — c'est le temps que met l'oscillation à
      s'installer, et il change avec la nuance ;
    - **relâcher une touche ne coupe pas le son** : la pression retombe et
      l'oscillation s'éteint d'elle-même en passant sous son seuil, avec son
      hystérésis. La note tient un peu plus bas qu'elle n'a démarré.
    """
    from PyQt6 import QtWidgets, QtCore
    import numpy as np

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    out = QtWidgets.QPlainTextEdit(); out.setReadOnly(True)
    out.setMaximumHeight(160)

    from .. import hybrid as _hyb
    instrument = QtWidgets.QComboBox(); instrument.addItems(sorted(_hyb.INSTRUMENTS))
    instrument.setCurrentText('clarinette')

    poly = QtWidgets.QSpinBox(); poly.setRange(1, 16); poly.setValue(6)
    gain = QtWidgets.QDoubleSpinBox()
    gain.setRange(0.0, 1.0); gain.setSingleStep(0.05); gain.setValue(0.4)

    expr = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    expr.setRange(0, 127); expr.setValue(100)
    expr.setToolTip("Nuance — molette de modulation (CC1) ou contrôleur à vent (CC2/CC11)")

    midi_port = QtWidgets.QComboBox()
    lbl = QtWidgets.QLabel("Aucun instrument préparé.")
    lbl.setWordWrap(True)

    def log(t):
        out.appendPlainText(t)

    # -- préparation -------------------------------------------------------
    def prepare():
        nom = instrument.currentText()
        btn_prep.setEnabled(False)
        log(f"préparation de « {nom} » : une perce par demi-ton, "
            f"puis accordage note à note…")

        def work(emit):
            import numpy as np
            from .. import live
            live.engine_library()
            inst = live.build_instrument(nom, lo=40, hi=88)
            rtf = live.realtime_factor(inst, n_voices=poly.value(), seconds=0.3)
            # ce que l'accordage a donné, mesuré sur le moteur et pas promis
            ecarts = []
            for n in range(inst.lo, inst.hi + 1, 6):
                f = live._frequence_jouee(inst.params_for(n),
                                          inst.level_default, inst.samplerate)
                if f:
                    ecarts.append(1200 * np.log2(f / live.midi_to_hz(n)))
            just = float(np.median(np.abs(ecarts))) if ecarts else float('nan')
            return inst, rtf, just

        def done(r):
            btn_prep.setEnabled(True)
            inst, rtf, just = r
            from .. import live
            state['live_inst'] = inst
            state['live_synth'] = live.Synth(inst, polyphony=poly.value(),
                                             gain=gain.value())
            lbl.setText(f"{nom} — {len(inst)} notes prêtes · "
                        f"×{rtf:.0f} le temps réel à {poly.value()} voix")
            log(f"  {len(inst)} notes · nuance nominale {inst.level_default:.4g} "
                f"{inst.control_unit} · ×{rtf:.0f} temps réel")
            log(f"  justesse mesurée sur le moteur : {just:.1f} cent d'écart "
                f"médian (accordage géométrique, pas de transposition)")
            if rtf < 2:
                log("  ⚠ marge faible : baisse la polyphonie si ça craque")

        def failed(m):
            btn_prep.setEnabled(True); log("erreur : " + m)

        _run_async(state, work, None, done, failed)

    # -- audio -------------------------------------------------------------
    def audio_start():
        syn = state.get('live_synth')
        if syn is None:
            log("prépare d'abord un instrument"); return
        try:
            import sounddevice as sd
        except Exception:
            log("sounddevice absent : pip install sounddevice"); return
        if state.get('live_stream') is not None:
            log("déjà en marche"); return

        syn.gain = gain.value()

        def cb(outdata, frames, time_info, status):
            if status:
                pass
            outdata[:, 0] = syn.render(frames)

        try:
            st = sd.OutputStream(samplerate=syn.inst.samplerate, channels=1,
                                 dtype='float32', blocksize=256, callback=cb)
            st.start()
        except Exception as e:
            log(f"impossible d'ouvrir la sortie audio : {e}"); return
        state['live_stream'] = st
        log(f"audio en marche — {syn.inst.samplerate:.0f} Hz, blocs de 256")

    def audio_stop():
        st = state.pop('live_stream', None)
        if st is not None:
            try:
                st.stop(); st.close()
            except Exception:
                pass
            log("audio arrêté")
        syn = state.get('live_synth')
        if syn is not None:
            syn.all_notes_off()

    # -- MIDI --------------------------------------------------------------
    def midi_scan():
        midi_port.clear()
        try:
            import mido
        except Exception:
            midi_port.addItem("mido absent — pip install mido python-rtmidi")
            return
        noms = mido.get_input_names()
        midi_port.addItems(noms or ["(aucun port MIDI)"])
        log(f"{len(noms)} port(s) MIDI") if noms else log("aucun port MIDI trouvé")

    def midi_open():
        syn = state.get('live_synth')
        if syn is None:
            log("prépare d'abord un instrument"); return
        try:
            import mido
        except Exception:
            log("mido absent : pip install mido python-rtmidi"); return
        nom = midi_port.currentText()
        if not nom or nom.startswith('('):
            log("aucun port MIDI sélectionné"); return
        if state.get('live_midi') is not None:
            log("port déjà ouvert"); return

        def on_msg(msg):
            s = state.get('live_synth')
            if s is None:
                return
            if msg.type == 'note_on' and msg.velocity > 0:
                s.note_on(msg.note, msg.velocity)
            elif msg.type in ('note_off', 'note_on'):
                s.note_off(msg.note)
            elif msg.type == 'control_change':
                if msg.control in (1, 2, 11):         # molette, souffle, expression
                    s.expression = msg.value / 127.0
                elif msg.control == 123:              # all notes off
                    s.all_notes_off()
            elif msg.type == 'pitchwheel':
                pass                                   # à faire : pitch bend continu

        try:
            port = mido.open_input(nom, callback=on_msg)
        except Exception as e:
            log(f"impossible d'ouvrir {nom} : {e}"); return
        state['live_midi'] = port
        log(f"MIDI ouvert sur « {nom} » — joue.")

    def midi_close():
        port = state.pop('live_midi', None)
        if port is not None:
            try:
                port.close()
            except Exception:
                pass
            log("MIDI fermé")

    # -- clavier de secours, pour essayer sans matériel ---------------------
    def touche(note):
        def f():
            syn = state.get('live_synth')
            if syn is None:
                log("prépare d'abord un instrument"); return
            syn.note_on(note, 100)
            QtCore.QTimer.singleShot(900, lambda: syn.note_off(note))
        return f

    clavier = QtWidgets.QWidget(); hb = QtWidgets.QHBoxLayout(clavier)
    hb.setContentsMargins(0, 0, 0, 0)
    for nom_note, n in [("do", 60), ("ré", 62), ("mi", 64), ("fa", 65),
                        ("sol", 67), ("la", 69), ("si", 71), ("do'", 72)]:
        b = QtWidgets.QPushButton(nom_note)
        b.setMaximumWidth(48)
        b.clicked.connect(touche(n))
        hb.addWidget(b)

    # -- suivi ---------------------------------------------------------------
    etat = QtWidgets.QLabel("—")
    tim = QtCore.QTimer(page)

    def tick():
        syn = state.get('live_synth')
        if syn is None:
            return
        syn.expression = expr.value() / 127.0
        syn.gain = gain.value()
        etat.setText(f"voix actives : {syn.active_voices} / {len(syn.voices)}"
                     f"   ·   nuance {100 * syn.expression:.0f} %"
                     f"   ·   audio {'en marche' if state.get('live_stream') else 'arrêté'}"
                     f"   ·   MIDI {'ouvert' if state.get('live_midi') else 'fermé'}")
    tim.timeout.connect(tick)
    tim.start(120)

    def export_wav():
        syn = state.get('live_synth')
        if syn is None:
            log("prépare d'abord un instrument"); return
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            page, "Enregistrer une note", f"{instrument.currentText()}.wav",
            "WAV (*.wav)")
        if not fn:
            return
        from scipy.io.wavfile import write
        from .. import live as _lv
        s2 = _lv.Synth(syn.inst, polyphony=1, gain=gain.value())
        s2.note_on(64, 100)
        bloc = [s2.render(2048) for _ in range(int(1.2 * syn.inst.samplerate / 2048))]
        s2.note_off(64)
        bloc += [s2.render(2048) for _ in range(int(0.8 * syn.inst.samplerate / 2048))]
        sig = np.concatenate(bloc)
        write(fn, int(syn.inst.samplerate), (np.clip(sig, -1, 1) * 32767).astype('int16'))
        log(f"→ {fn}  (attaque, tenue, puis extinction physique après relâché)")

    btn_prep = QtWidgets.QPushButton("Préparer"); btn_prep.clicked.connect(prepare)
    b_on = QtWidgets.QPushButton("Audio ▶"); b_on.clicked.connect(audio_start)
    b_off = QtWidgets.QPushButton("Audio ■"); b_off.clicked.connect(audio_stop)
    b_scan = QtWidgets.QPushButton("Chercher MIDI"); b_scan.clicked.connect(midi_scan)
    b_mon = QtWidgets.QPushButton("Ouvrir MIDI"); b_mon.clicked.connect(midi_open)
    b_moff = QtWidgets.QPushButton("Fermer MIDI"); b_moff.clicked.connect(midi_close)
    b_wav = QtWidgets.QPushButton("Exporter un WAV"); b_wav.clicked.connect(export_wav)

    lay.addWidget(_row("Instrument", instrument, "Polyphonie", poly,
                       "Gain", gain, btn_prep))
    lay.addWidget(lbl)
    lay.addWidget(_row(b_on, b_off, "Port MIDI", midi_port, b_scan, b_mon, b_moff))
    lay.addWidget(_row("Nuance", expr))
    lay.addWidget(_row(QtWidgets.QLabel("Clavier d'essai :"), clavier))
    lay.addWidget(etat)
    lay.addWidget(out)
    lay.addWidget(_row(b_wav))
    midi_scan()
    return page


def main() -> int:
    """Point d'entrée `banc-recherche`."""
    try:
        from PyQt6 import QtWidgets
    except Exception:
        print("PyQt6 n'est pas installé. `pip install -r requirements.txt`.", file=sys.stderr)
        print(f"Config par défaut : {DEFAULT}")
        return 1
    app = QtWidgets.QApplication(sys.argv)
    win = _build(DEFAULT)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
