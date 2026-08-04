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
    tabs.addTab(_tab_seuil(state, plot_widget), "Seuil auto-entretien")
    tabs.addTab(_tab_doe(state), "Plan d'expériences")
    tabs.addTab(_tab_campaigns(state), "Campagnes")

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
        try:
            freqs, H = excitation.response(state["cfg"].audio, sw)
            res = excitation.resonances(freqs, H)
            if hasattr(plot, "plot"):
                plot.clear(); plot.plot(freqs, abs(H))
            table.setRowCount(len(res))
            for i, (fr, mag, ph) in enumerate(res):
                for j, v in enumerate((f"{fr:.1f}", f"{mag:.3g}", f"{ph:.2f}")):
                    table.setItem(i, j, QtWidgets.QTableWidgetItem(v))
            status.setText(f"{len(res)} résonances")
        except Exception as e:
            status.setText("erreur : " + str(e))

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
        try:
            r = analysis.praat_calcs(state["sound"], state["sr"])
            results.setText(
                f"Tresp = {r.tresp_s*1000:.1f} ms · F0 = {r.mean_fund_hz:.2f} Hz · "
                f"F1–F4 = {r.f1:.0f}/{r.f2:.0f}/{r.f3:.0f}/{r.f4:.0f} Hz · HNR = {r.hnr_db:.1f} dB")
            if hasattr(plot, "plot"):
                plot.clear()
                plot.plot(r.env_t, r.env / (abs(r.env).max() or 1))
        except Exception as e:
            results.setText("erreur : " + str(e))

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
    prog = QtWidgets.QProgressBar()
    table = QtWidgets.QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(["#", "S", "P", "Clap", "Tresp", "Z"])
    status = QtWidgets.QLabel("")

    def parse(le):
        return tuple(float(x) for x in le.text().split(",") if x.strip())

    def run():
        d.sections_mm, d.pressures_pa, d.clapets_deg = parse(sec), parse(pre), parse(cla)
        total = len(d.sections_mm) * len(d.pressures_pa) * len(d.clapets_deg)
        prog.setMaximum(total); table.setRowCount(0)

        def on_prog(k, tot, msg):
            prog.setValue(k); status.setText(f"{k}/{tot} — {msg}")
            QtWidgets.QApplication.processEvents()

        try:
            for pt in doe.run(state["cfg"], link=state["link"], progress=on_prog):
                r = table.rowCount(); table.insertRow(r)
                vals = (pt.idx, pt.section_mm, pt.pressure_pa, pt.clapet_deg,
                        f"{pt.tresp_ms:.1f}", f"{pt.impedance:.1f}")
                for j, v in enumerate(vals):
                    table.setItem(r, j, QtWidgets.QTableWidgetItem(str(v)))
                QtWidgets.QApplication.processEvents()
            status.setText(f"terminé → {state['cfg'].csv_path}")
        except Exception as e:
            status.setText("erreur : " + str(e))

    btn = QtWidgets.QPushButton("Lancer le DOE"); btn.clicked.connect(run)
    lay.addWidget(_row("Section", sec, "Pression", pre, "Clapet", cla, btn))
    lay.addWidget(prog); lay.addWidget(table); lay.addWidget(status)
    return page


# ---- 7. Campagnes (campaigns) ----------------------------------------------
def _tab_campaigns(state):
    from PyQt6 import QtWidgets
    from .. import campaigns, analysis

    page = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(page)
    info = QtWidgets.QLabel("Ouvrir un HDF5 de campagne (Mesures.py).")
    idx = QtWidgets.QLineEdit("0,0,0,0")   # Ppos,Section,Pression,Clapet
    out = QtWidgets.QLabel("—")
    state["_camp"] = {"f": None}

    def open_h5():
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(page, "HDF5", "", "HDF5 (*.hdf5 *.h5)")
        if not fn:
            return
        try:
            f, present = campaigns.open_campaign(fn)
            state["_camp"]["f"] = f
            info.setText(f"{fn} — datasets : {', '.join(present.keys())}")
        except Exception as e:
            info.setText("erreur : " + str(e))

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
    lay.addWidget(_row(b1)); lay.addWidget(info)
    lay.addWidget(_row("Ppos,Sec,Pres,Clap", idx, b2)); lay.addWidget(out)
    lay.addStretch(1)
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
