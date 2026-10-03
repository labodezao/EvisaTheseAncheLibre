"""Anches (reedgui) : décrire une languette par tronçons et voir ses modes.

Reprise de FreeReedGUI d'Ewen (2020-2021, Tkinter + matplotlib, `km.py`, `fleche.py`) :
on garde l'idée (l'anche par tronçons, le profil, la déformée, Ouvrir/Enregistrer), on
refait le reste pour que ce soit juste et confortable.

- Un tableau des tronçons, en mm, modifiable directement (double-clic sur une case).
- Le profil à droite (vue de dessus à l'échelle, vue de côté), mis à jour à chaque changement.
- Les 3 à 5 premiers modes : fréquence (Euler-Bernoulli exact), note la plus proche et
  écart en cents ; Rayleigh-Ritz (la méthode de km.py, 20 modes de base) en contrôle.
  Un clic sur un mode trace sa déformée.
- Ouvrir / Enregistrer au format de la banque d'anches (CSV) ; Ouvrir lit aussi l'ancien
  `matrix.txt`. Exporter une image, exporter le yaml du modèle. Vérifier avec Elmer.

Le calcul est dans `banc_recherche/languette.py` (le même que pour Elmer et le modèle
semi-analytique) ; ce fichier ne fait que l'interface. La partie sans fenêtre (`Etat`)
est testée dans `tests/test_reedgui.py`.

Lancer : double-clic sur « Anches (reedgui).cmd », ou
    J:\\claude\\venv\\Scripts\\python.exe research\\reedgui\\reedgui.py [banque.csv | matrix.txt]
"""
from __future__ import annotations

import os
import sys
import threading
import traceback

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RECHERCHE = os.path.abspath(os.path.join(ICI, ".."))
sys.path.insert(0, RECHERCHE)
from banc_recherche.banque_anches import (Anche, ecrire_banque, ecrire_yaml, importer,  # noqa: E402
                                          nom_note, note_hz)
from banc_recherche.languette import (MATERIAUX, Languette, Troncon, euler_bernoulli,  # noqa: E402
                                      forme_euler_bernoulli, materiau, rayleigh_ritz)

COLONNES = [("longueur_mm", "Longueur"), ("largeur_debut_mm", "Largeur début"),
            ("largeur_fin_mm", "Largeur fin"), ("epaisseur_debut_mm", "Épaisseur début"),
            ("epaisseur_fin_mm", "Épaisseur fin"), ("materiau", "Matériau")]


def _nombre(texte, nom):
    t = str(texte).strip().replace(",", ".")
    if t == "":
        raise ValueError(f"{nom} : case vide")
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{nom} : « {texte} » n'est pas un nombre")
    if v <= 0:
        raise ValueError(f"{nom} : doit être plus grand que 0")
    return v


def _txt(v):
    return f"{float(v):.4g}".replace(".", ",")


# =============================================================================
# L'état de l'anche, sans fenêtre (testable)
# =============================================================================
class Etat:
    """Une anche en cours d'édition : tronçons (textes en mm), nom, note visée, masse au bout."""

    def __init__(self):
        self.id = "nouvelle anche"
        self.note = ""
        self.masse_bout_g = ""
        self.troncons = [dict(longueur_mm="30", largeur_debut_mm="3,5", largeur_fin_mm="3,5",
                              epaisseur_debut_mm="0,3", epaisseur_fin_mm="0,3", materiau="acier")]
        self.anche = None            # l'Anche de la banque (ses autres champs sont gardés)
        self.fichier = None

    # -- tronçons
    def ajouter(self, apres=None):
        modele = dict(self.troncons[apres if apres is not None else -1])
        i = (apres + 1) if apres is not None else len(self.troncons)
        self.troncons.insert(i, modele)
        return i

    def dupliquer(self, i):
        self.troncons.insert(i + 1, dict(self.troncons[i]))
        return i + 1

    def supprimer(self, i):
        if len(self.troncons) <= 1:
            raise ValueError("il faut au moins un tronçon")
        del self.troncons[i]

    def deplacer(self, i, sens):
        j = i + sens
        if 0 <= j < len(self.troncons):
            self.troncons[i], self.troncons[j] = self.troncons[j], self.troncons[i]
            return j
        return i

    # -- calcul
    def languette(self):
        """La languette (SI), ou ValueError avec un message simple (tronçon n°...)."""
        tr = []
        for k, t in enumerate(self.troncons, start=1):
            q = f"tronçon {k}"
            L = _nombre(t["longueur_mm"], f"{q}, longueur")
            b0 = _nombre(t["largeur_debut_mm"], f"{q}, largeur début")
            b1 = _nombre(t["largeur_fin_mm"] or t["largeur_debut_mm"], f"{q}, largeur fin")
            e0 = _nombre(t["epaisseur_debut_mm"], f"{q}, épaisseur début")
            e1 = _nombre(t["epaisseur_fin_mm"] or t["epaisseur_debut_mm"], f"{q}, épaisseur fin")
            if L > 200 or max(b0, b1) > 30 or max(e0, e1) > 5:
                raise ValueError(f"{q} : une valeur paraît trop grande (tout est en mm)")
            if min(e0, e1) < 0.01:
                raise ValueError(f"{q} : épaisseur plus fine que 0,01 mm (tout est en mm)")
            try:
                materiau(t["materiau"] or "acier")
            except ValueError:
                raise ValueError(f"{q} : matériau « {t['materiau']} » inconnu ; choisir dans la liste "
                                 "ou écrire « 200 GPa / 7850 »")
            tr.append(Troncon(L * 1e-3, (b0 * 1e-3, b1 * 1e-3), (e0 * 1e-3, e1 * 1e-3), t["materiau"] or "acier"))
        masses = []
        if str(self.masse_bout_g).strip():
            m = _nombre(self.masse_bout_g, "masse au bout (g)")
            Ltot = sum(t.longueur for t in tr)
            masses.append((Ltot - 1e-3, m * 1e-3))
        return Languette(tr, masses, nom=self.id)

    def calculer(self, n_modes=5):
        """(languette, lignes) ; une ligne par mode : f exacte, note, cents, f Rayleigh-Ritz."""
        lang = self.languette()
        f = euler_bernoulli(lang, n_modes)
        rr = rayleigh_ritz(lang, n_modes, n_base=20)[0]
        lignes = []
        for k, fk in enumerate(f, start=1):
            nm, ct = nom_note(fk)
            lignes.append(dict(mode=k, f_hz=float(fk), note=nm, cents=ct,
                               f_rr_hz=float(rr[k - 1]) if k <= len(rr) else float("nan")))
        return lang, lignes

    def ecart_cible(self, f1):
        """Écart (cents) entre f1 et la note visée, ou None."""
        try:
            fc = note_hz(self.note) if str(self.note).strip() else None
        except ValueError:
            return None
        return None if not fc else 1200 * np.log2(f1 / fc)

    # -- fichiers
    def ouvrir(self, chemin, id_choisi=None):
        """Banque CSV (l'anche `id_choisi`, sinon la première) ou ancien matrix.txt.
        Renvoie la liste des id du fichier (pour choisir)."""
        self.fichier = chemin
        if chemin.lower().endswith(".csv"):
            anches, pb = importer(chemin)
            err = [str(p) for p in pb if p.niveau == "erreur"]
            if not anches:
                raise ValueError("aucune anche dans ce fichier" + (" : " + err[0] if err else ""))
            a = next((x for x in anches if x.id == id_choisi), anches[0])
            self.anche = a
            self.id = a.id
            c_note = a.champs.get("note", {})
            self.note = (c_note.get("valeur") or "") if (not c_note.get("a_mesurer") or c_note.get("estime")) else ""
            mb = a.valeur("masse_bout")
            self.masse_bout_g = _txt(mb) if isinstance(mb, (int, float)) and not isinstance(mb, bool) else ""
            self.troncons = [dict(longueur_mm=_txt(t["longueur_mm"]), largeur_debut_mm=_txt(t["largeur_mm"][0]),
                                  largeur_fin_mm=_txt(t["largeur_mm"][1]), epaisseur_debut_mm=_txt(t["epaisseur_mm"][0]),
                                  epaisseur_fin_mm=_txt(t["epaisseur_mm"][1]), materiau=t.get("materiau", "acier"))
                             for t in a.troncons]
            return [x.id for x in anches]
        # ancien format reedgui : L, densité, largeur, épaisseur, E (SI), séparateur virgule
        lang = Languette.depuis_matrice(chemin)
        self.anche = None
        self.id = os.path.splitext(os.path.basename(chemin))[0]
        self.note, self.masse_bout_g = "", ""
        self.troncons = []
        for t in lang.troncons:
            nom = next((k for k, v in MATERIAUX.items() if abs(v["E"] - t.E) < 1e6 and abs(v["rho"] - t.rho) < 1), None)
            self.troncons.append(dict(longueur_mm=_txt(t.longueur * 1e3), largeur_debut_mm=_txt(t.largeur[0] * 1e3),
                                      largeur_fin_mm=_txt(t.largeur[1] * 1e3),
                                      epaisseur_debut_mm=_txt(t.epaisseur[0] * 1e3),
                                      epaisseur_fin_mm=_txt(t.epaisseur[1] * 1e3),
                                      materiau=nom or f"{t.E / 1e9:g} GPa / {t.rho:g}"))
        return [self.id]

    def vers_anche(self):
        """L'Anche de la banque (les autres champs de l'anche ouverte sont gardés)."""
        self.languette()                                    # contrôle d'abord
        a = Anche(id=self.id.strip() or "anche")
        if self.anche is not None:
            a.champs = {k: dict(v) for k, v in self.anche.champs.items()}
        if str(self.note).strip():
            note_hz(self.note)                              # contrôle
            a.champs["note"] = {"valeur": self.note.strip(), "a_mesurer": False}
        if str(self.masse_bout_g).strip():
            a.champs["masse_bout"] = {"valeur": _nombre(self.masse_bout_g, "masse au bout"), "a_mesurer": False}

        def f(v):
            return float(str(v).replace(",", "."))
        a.troncons = [dict(longueur_mm=f(t["longueur_mm"]),
                           largeur_mm=[f(t["largeur_debut_mm"]), f(t["largeur_fin_mm"] or t["largeur_debut_mm"])],
                           epaisseur_mm=[f(t["epaisseur_debut_mm"]), f(t["epaisseur_fin_mm"] or t["epaisseur_debut_mm"])],
                           materiau=(t["materiau"] or "acier").strip().lower())
                      for t in self.troncons]
        return a

    def enregistrer(self, chemin):
        """Dans une banque CSV : remplace cette anche (même id) ou l'ajoute ; les autres
        anches du fichier sont gardées telles quelles."""
        a = self.vers_anche()
        anches = []
        if os.path.exists(chemin):
            anches, _ = importer(chemin)
        anches = [x for x in anches if x.id != a.id] + [a]
        ecrire_banque(anches, chemin)
        self.fichier, self.anche = chemin, a
        return chemin


# =============================================================================
# La fenêtre
# =============================================================================
class Fenetre:
    def __init__(self, racine, etat=None):
        import tkinter as tk
        from tkinter import font as tkfont, ttk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        self.tk, self.ttk = tk, ttk
        self.racine = racine
        self.etat = etat or Etat()
        self.n_modes = tk.IntVar(value=5)
        self.mode_choisi = 1
        self.lang = None
        self.lignes = []
        self.f_elmer = None
        self._attente = None
        racine.title("Anches (reedgui)")
        L, H = racine.winfo_screenwidth(), racine.winfo_screenheight()
        racine.geometry(f"{int(L * 0.94)}x{int(H * 0.86)}+{int(L * 0.03)}+10")
        for nom in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
            tkfont.nametofont(nom).configure(size=12)
        hauteur = tkfont.nametofont("TkDefaultFont").metrics("linespace")
        style = ttk.Style()
        style.configure("Treeview", rowheight=int(hauteur * 1.5))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

        # -- barre du haut
        haut = ttk.Frame(racine, padding=6)
        haut.pack(side="top", fill="x")
        for texte, cmd in (("Ouvrir", self.ouvrir), ("Enregistrer", self.enregistrer),
                           ("Exporter l'image", self.exporter_image), ("Exporter le yaml", self.exporter_yaml)):
            ttk.Button(haut, text=texte, command=self._sur(cmd)).pack(side="left", padx=3)
        self.bouton_elmer = ttk.Button(haut, text="Vérifier avec Elmer", command=self._sur(self.elmer))
        self.bouton_elmer.pack(side="left", padx=12)
        try:
            sys.path.insert(0, os.path.join(RECHERCHE, "fem"))
            import elmer_outils
            if not elmer_outils.disponible():
                raise ImportError
        except Exception:                                               # noqa: BLE001
            self.bouton_elmer.state(["disabled"])

        info = ttk.Frame(racine, padding=(6, 0))
        info.pack(side="top", fill="x")
        self.v_id = tk.StringVar(value=self.etat.id)
        self.v_note = tk.StringVar(value=self.etat.note)
        self.v_masse = tk.StringVar(value=self.etat.masse_bout_g)
        for lab, var, w in (("Nom", self.v_id, 22), ("Note visée (la3, sib2...)", self.v_note, 8),
                            ("Masse au bout (g, vide si aucune)", self.v_masse, 7)):
            ttk.Label(info, text=lab).pack(side="left", padx=(8, 3))
            ttk.Entry(info, textvariable=var, width=w).pack(side="left")
            var.trace_add("write", lambda *a: self._changement())
        ttk.Label(info, text="Modes").pack(side="left", padx=(16, 3))
        ttk.Spinbox(info, from_=3, to=5, width=3, textvariable=self.n_modes,
                    command=self._changement).pack(side="left")

        # -- corps : à gauche les tableaux, à droite les dessins
        corps = ttk.Panedwindow(racine, orient="horizontal")
        corps.pack(fill="both", expand=True)
        gauche = ttk.Frame(corps, padding=6)
        droite = ttk.Frame(corps, padding=6)
        corps.add(gauche, weight=1)
        corps.add(droite, weight=1)

        ttk.Label(gauche, text="Tronçons, du pied (rivet) au bout. Tout est en mm. "
                               "Double-clic sur une case pour la changer.", wraplength=600).pack(anchor="w")
        self.table = ttk.Treeview(gauche, columns=["n"] + [c for c, _ in COLONNES], show="headings", height=6)
        self.table.heading("n", text="N°")
        self.table.column("n", width=40, anchor="center")
        for c, t in COLONNES:
            self.table.heading(c, text=t)
            self.table.column(c, width=95 if c != "materiau" else 130, anchor="center", stretch=True)
        self.table.pack(fill="x", pady=4)
        self.table.bind("<Double-1>", self._editer)
        boutons = ttk.Frame(gauche)
        boutons.pack(fill="x")
        for texte, cmd in (("Ajouter", self.ajouter), ("Dupliquer", self.dupliquer), ("Supprimer", self.supprimer),
                           ("Monter", lambda: self.deplacer(-1)), ("Descendre", lambda: self.deplacer(1))):
            ttk.Button(boutons, text=texte, command=self._sur(cmd)).pack(side="left", padx=3)

        ttk.Label(gauche, text="Modes de flexion (un clic : voir la déformée)").pack(anchor="w", pady=(14, 0))
        self.modes = ttk.Treeview(gauche, columns=("mode", "f", "note", "cents", "rr", "elmer"),
                                  show="headings", height=5)
        for c, t, w in (("mode", "Mode", 55), ("f", "Fréquence (Hz)", 125), ("note", "Note", 70),
                        ("cents", "Écart (cents)", 105), ("rr", "Rayleigh-Ritz (Hz)", 140),
                        ("elmer", "Elmer (Hz)", 100)):
            self.modes.heading(c, text=t)
            self.modes.column(c, width=w, anchor="center")
        self.modes.pack(fill="x", pady=4)
        self.modes.bind("<<TreeviewSelect>>", self._choisir_mode)
        self.resume = ttk.Label(gauche, text="", wraplength=600, justify="left")
        self.resume.pack(anchor="w", pady=6)
        self.message = tk.Label(gauche, text="", fg="#b00020", wraplength=600, justify="left",
                                font=("Segoe UI", 13, "bold"))
        self.message.pack(anchor="w", pady=6)

        self.fig = Figure(figsize=(6, 6), dpi=90)
        self.ax_dessus = self.fig.add_subplot(311)
        self.ax_cote = self.fig.add_subplot(312, sharex=self.ax_dessus)
        self.ax_mode = self.fig.add_subplot(313, sharex=self.ax_dessus)
        self.canvas = FigureCanvasTkAgg(self.fig, master=droite)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._remplir_table()
        self._sur(self.recalculer)()

    # -- outils
    def _sur(self, f):
        """Toute action passe par ici : une erreur devient un message, jamais un plantage."""
        def g(*a):
            try:
                self.message.config(text="")
                return f(*a)
            except ValueError as ex:
                self.message.config(text=str(ex))
            except Exception as ex:                                     # noqa: BLE001
                traceback.print_exc()
                self.message.config(text=f"Quelque chose n'a pas marché : {ex}")
        return g

    def _remplir_table(self, choisir=None):
        self.table.delete(*self.table.get_children())
        for k, t in enumerate(self.etat.troncons, start=1):
            self.table.insert("", "end", iid=str(k - 1), values=[k] + [t[c] for c, _ in COLONNES])
        if choisir is not None:
            self.table.selection_set(str(choisir))

    def _ligne_choisie(self):
        s = self.table.selection()
        if not s:
            raise ValueError("choisir d'abord un tronçon dans le tableau (un clic)")
        return int(s[0])

    def _editer(self, ev):
        ttk = self.ttk
        ligne, col = self.table.identify_row(ev.y), self.table.identify_column(ev.x)
        if not ligne or col == "#1":
            return
        i, c = int(ligne), COLONNES[int(col[1:]) - 2][0]
        x, y, w, h = self.table.bbox(ligne, col)
        if c == "materiau":
            champ = ttk.Combobox(self.table, values=list(MATERIAUX) + ["200 GPa / 7850"])
        else:
            champ = ttk.Entry(self.table)
        champ.insert(0, self.etat.troncons[i][c])
        champ.place(x=x, y=y, width=max(w, 120), height=h)
        champ.focus_set()
        champ.select_range(0, "end")
        fait = []

        def valider(*_):
            if fait:
                return
            fait.append(1)
            self.etat.troncons[i][c] = champ.get().strip()
            champ.destroy()
            self._remplir_table(i)
            self._changement()
        champ.bind("<Return>", valider)
        champ.bind("<Tab>", valider)
        champ.bind("<FocusOut>", valider)
        champ.bind("<Escape>", lambda *_: (fait.append(1), champ.destroy()))

    def _changement(self):
        """Recalcul en direct, 300 ms après la dernière frappe."""
        if self._attente:
            self.racine.after_cancel(self._attente)
        self._attente = self.racine.after(300, self._sur(self.recalculer))

    # -- actions
    def ajouter(self):
        s = self.table.selection()
        i = self.etat.ajouter(int(s[0]) if s else None)
        self._remplir_table(i); self._changement()

    def dupliquer(self):
        i = self.etat.dupliquer(self._ligne_choisie())
        self._remplir_table(i); self._changement()

    def supprimer(self):
        self.etat.supprimer(self._ligne_choisie())
        self._remplir_table(); self._changement()

    def deplacer(self, sens):
        i = self.etat.deplacer(self._ligne_choisie(), sens)
        self._remplir_table(i); self._changement()

    def recalculer(self):
        self.etat.id, self.etat.note, self.etat.masse_bout_g = self.v_id.get(), self.v_note.get(), self.v_masse.get()
        self.lang, self.lignes = self.etat.calculer(int(self.n_modes.get()))
        self.modes.delete(*self.modes.get_children())
        for l in self.lignes:
            fe = ""
            if self.f_elmer and l["mode"] <= len(self.f_elmer):
                fe = f"{self.f_elmer[l['mode'] - 1]:.1f}"
            self.modes.insert("", "end", iid=str(l["mode"]),
                              values=(l["mode"], f"{l['f_hz']:.2f}", l["note"], f"{l['cents']:+.0f}",
                                      f"{l['f_rr_hz']:.2f}", fe))
        f1 = self.lignes[0]["f_hz"]
        ec = self.etat.ecart_cible(f1)
        rr = 100 * (self.lignes[0]["f_rr_hz"] / f1 - 1)
        self.resume.config(text=(f"Longueur libre {self.lang.L * 1e3:.2f} mm, masse {self.lang.masse() * 1e3:.3f} g. "
                                 f"Mode 1 : {f1:.2f} Hz" +
                                 (f", soit {ec:+.0f} cents par rapport à la note visée." if ec is not None else ".") +
                                 f" Contrôle Rayleigh-Ritz : {rr:+.2f} %."))
        self.mode_choisi = min(self.mode_choisi, len(self.lignes))
        self.dessiner()

    def _choisir_mode(self, *_):
        s = self.modes.selection()
        if s:
            self.mode_choisi = int(s[0])
            self._sur(self.dessiner)()

    def dessiner(self):
        lang = self.lang
        if lang is None:
            return
        x = np.linspace(0, lang.L, 800)
        b, t, _, _ = lang.profil(x)
        X = x * 1e3
        for ax in (self.ax_dessus, self.ax_cote, self.ax_mode):
            ax.clear()
        self.ax_dessus.fill_between(X, -b * 500, b * 500, color="#c9a227", ec="#6b5000")
        self.ax_dessus.set_aspect("equal", adjustable="datalim")
        self.ax_dessus.set_title("Vue de dessus (à l'échelle, mm)", fontsize=12)
        exag = 10
        self.ax_cote.fill_between(X, 0, t * 1e3 * exag, color="#8a8f98", ec="#333")
        self.ax_cote.set_title(f"Vue de côté : épaisseur agrandie {exag} fois (max {t.max() * 1e3:.2f} mm)",
                               fontsize=12)
        self.ax_cote.set_yticks([])
        for xm, m in lang.masses:
            self.ax_cote.axvline(xm * 1e3, color="#b00020", lw=2)
            self.ax_cote.text(xm * 1e3, t.max() * 1e3 * exag, f" {m * 1e3:g} g", color="#b00020", va="top")
        for e in lang.bords[1:-1]:
            self.ax_dessus.axvline(e * 1e3, color="#555", lw=0.6, ls=":")
            self.ax_cote.axvline(e * 1e3, color="#555", lw=0.6, ls=":")
        l = self.lignes[self.mode_choisi - 1]
        y = forme_euler_bernoulli(lang, l["f_hz"], x)
        self.ax_mode.plot(X, y, lw=2.5, color="#1f5fa8")
        self.ax_mode.axhline(0, color="#999", lw=0.8)
        self.ax_mode.set_title(f"Déformée du mode {l['mode']} : {l['f_hz']:.1f} Hz ({l['note']})", fontsize=12)
        self.ax_mode.set_xlabel("distance au pied (mm)")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def ouvrir(self):
        from tkinter import filedialog, simpledialog
        ch = filedialog.askopenfilename(title="Ouvrir une anche", initialdir=os.path.join(RECHERCHE, "fem", "anche"),
                filetypes=[("Banque d'anches", "*.csv"), ("Ancien reedgui (matrix.txt)", "*.txt"), ("Tous", "*.*")])
        if not ch:
            return
        ids = self.etat.ouvrir(ch)
        if len(ids) > 1:
            choix = simpledialog.askstring("Quelle anche ?", "Anches du fichier :\n" + "\n".join(ids) +
                                           "\n\nÉcrire son nom :", initialvalue=ids[0], parent=self.racine)
            if choix and choix in ids:
                self.etat.ouvrir(ch, choix)
        self._depuis_etat()

    def _depuis_etat(self):
        self.v_id.set(self.etat.id); self.v_note.set(self.etat.note); self.v_masse.set(self.etat.masse_bout_g)
        self.f_elmer = None
        self._remplir_table()
        self.recalculer()

    def enregistrer(self):
        from tkinter import filedialog
        self.recalculer()
        defaut = os.path.basename(self.etat.fichier) if self.etat.fichier and self.etat.fichier.endswith(".csv") \
            else "banque_anches.csv"
        ch = filedialog.asksaveasfilename(title="Enregistrer dans une banque d'anches", defaultextension=".csv",
                                          initialdir=os.path.join(RECHERCHE, "fem", "anche"), initialfile=defaut,
                                          confirmoverwrite=False, filetypes=[("Banque d'anches", "*.csv")])
        if ch:
            self.etat.enregistrer(ch)
            self.resume.config(text=f"Enregistrée dans {ch} (les autres anches du fichier sont gardées)")

    def exporter_image(self):
        from tkinter import filedialog
        ch = filedialog.asksaveasfilename(title="Exporter l'image", defaultextension=".png",
                                          initialfile=f"{self.etat.id}.png", filetypes=[("Image PNG", "*.png")])
        if ch:
            self.fig.savefig(ch, dpi=150)
            self.resume.config(text=f"Image : {ch}")

    def exporter_yaml(self):
        from tkinter import filedialog
        if not (self.etat.fichier and self.etat.fichier.endswith(".csv")):
            raise ValueError("enregistrer d'abord l'anche dans une banque (.csv)")
        self.etat.enregistrer(self.etat.fichier)
        ch = filedialog.asksaveasfilename(title="Exporter le yaml du modèle", defaultextension=".yaml",
                                          initialdir=os.path.join(RECHERCHE, "fem", "anche"),
                                          initialfile="anches_r12.yaml", filetypes=[("yaml", "*.yaml")])
        if ch:
            anches, pb = importer(self.etat.fichier)
            err = [str(p) for p in pb if p.niveau == "erreur"]
            if err:
                raise ValueError("la banque a des erreurs : " + err[0])
            ecrire_yaml(anches, ch, self.etat.fichier)
            self.resume.config(text=f"yaml écrit : {ch}")

    def elmer(self):
        sys.path.insert(0, os.path.join(RECHERCHE, "fem", "anche"))
        import languette_modes
        lang = self.etat.languette()
        n = int(self.n_modes.get())
        self.bouton_elmer.state(["disabled"])
        self.resume.config(text="Elmer calcule (10 à 30 secondes)...")

        def travail():
            try:
                r = languette_modes.modes_elmer(lang, "reedgui_" + self.etat.id, n_modes=n + 4, encastrement="pied")
                f = [m["f_Hz"] for m in r["modes"] if m["type"] == "flexion"]
                autres = ", ".join(f"{m['f_Hz']:.0f} Hz ({m['type']})" for m in r["modes"] if m["type"] != "flexion")
                self.racine.after(0, lambda: self._fin_elmer(f, autres))
            except Exception as ex:                                      # noqa: BLE001
                msg = f"Elmer : {ex}"
                self.racine.after(0, lambda: self.message.config(text=msg))
            finally:
                self.racine.after(0, lambda: self.bouton_elmer.state(["!disabled"]))
        threading.Thread(target=travail, daemon=True).start()

    def _fin_elmer(self, f, autres):
        self.f_elmer = f
        self._sur(self.recalculer)()
        self.resume.config(text=self.resume.cget("text") + f"\nElmer (3D, encastré au pied) : autres modes {autres}.")


def net_sur_ecran():
    """Windows : dessiner à la vraie résolution (sinon, avec l'affichage agrandi à 150 %,
    tout est flou et la fenêtre déborde de l'écran)."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:                                                   # noqa: BLE001
        pass


def main(argv=None):
    import tkinter as tk
    net_sur_ecran()
    argv = sys.argv[1:] if argv is None else argv
    etat = Etat()
    if argv:
        etat.ouvrir(argv[0])
    racine = tk.Tk()
    Fenetre(racine, etat)
    racine.mainloop()


if __name__ == "__main__":
    main()
