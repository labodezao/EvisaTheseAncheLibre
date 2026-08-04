"""Fenêtre principale du banc de recherche (PyQt6).

Onglets : Excitation (sweep EM → résonances/phase), DOE (plan d'expériences),
Analyse (Praat : Tresp, formants, impédance). Squelette : la logique vit dans
les modules `banc_recherche.*`, la GUI n'est qu'un pilote.
"""
from __future__ import annotations

import sys

from ..config import DEFAULT


def _build_window():
    from PyQt6 import QtWidgets   # import différé (la GUI n'est requise qu'ici)

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("Banc de recherche — anches libres")
    tabs = QtWidgets.QTabWidget()

    for name in ("Excitation EM", "Plan d'expériences", "Analyse"):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.addWidget(QtWidgets.QLabel(
            f"« {name} » — à câbler sur banc_recherche.* "
            "(excitation / doe / analysis)."))
        tabs.addTab(page, name)

    win.setCentralWidget(tabs)
    win.resize(1000, 640)
    return win


def main() -> int:
    """Point d'entrée `banc-recherche`."""
    try:
        from PyQt6 import QtWidgets
    except Exception:
        print("PyQt6 n'est pas installé. `pip install -r requirements.txt`.",
              file=sys.stderr)
        print(f"Config par défaut : {DEFAULT}")
        return 1
    app = QtWidgets.QApplication(sys.argv)
    win = _build_window()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
