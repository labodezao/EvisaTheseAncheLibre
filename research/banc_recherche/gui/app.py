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
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(xx, phi)
            out.setText(f"états stables (minima du potentiel) : {len(mins)} "
                        f"→ {'bistable (bifurcation)' if len(mins) >= 2 else 'monostable'}")
            _savefig(plots.drift_diffusion_plot(km), "kramers_moyal.png")
            _savefig(plots.potential_plot(xx, phi), "potentiel.png")
        except Exception as e:
            out.setText("erreur : " + str(e))

    b1 = QtWidgets.QPushButton("Diagramme (CSV rampe)"); b1.clicked.connect(diagram)
    b2 = QtWidgets.QPushButton("Kramers-Moyal / potentiel (WAV)"); b2.clicked.connect(stochastic)
    lay.addWidget(_row(b1, b2)); lay.addWidget(plot); lay.addWidget(out)
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
