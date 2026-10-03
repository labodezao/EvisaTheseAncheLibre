"""La banque d'anches d'Ewen : un CSV à remplir à la main (ou à dicter), un yaml produit.

Le chemin, une seule source de vérité
-------------------------------------
    banque_anches.csv  (Ewen le remplit, tableur ou éditeur de texte)
        |  importer()  : contrôle des unités et des valeurs absurdes
        v
    anches_r12.yaml    (PRODUIT, ne pas modifier à la main)
        |  charger_yaml()
        v
    Languette (banc_recherche/languette.py) -> Elmer, Euler-Bernoulli, Rayleigh-Ritz,
                                               modèle semi-analytique, recalage, reedgui

Le format du CSV
----------------
Séparateur `;` (celui d'Excel en français), virgule décimale acceptée. Une seule ligne
d'en-tête (les noms de colonnes ci-dessous), puis, pour chaque anche :
- une ligne `anche` : ce qui décrit l'anche entière ;
- une ligne `troncon` par tronçon, de l'encastrement (le pied de la fente) jusqu'au bout.
Les lignes vides et celles qui commencent par `#` sont ignorées.

Colonnes d'un tronçon (mm) : longueur_mm ; largeur_debut_mm ; largeur_fin_mm ;
epaisseur_debut_mm ; epaisseur_fin_mm ; materiau (acier si vide). Une fin vide = le début
(tronçon constant). Les 5 épaisseurs mesurées au palmer font 4 tronçons : de la mesure 1 à
la 2, de la 2 à la 3, etc.

Colonnes d'une anche : id ; instrument ; rang ; note (la3, sib2, A4 ou 440) ; sens
(pousse / tire) ; position (interieure / exterieure) ; chambre (numéro dans le rang) ;
levee_mm (levée du bout au repos) ; fente_longueur_mm ; fente_largeur_mm ; plaque_mm
(épaisseur de la plaque) ; masse_bout (non, oui, ou sa masse en g) ; rivet_mm (du centre
du rivet au pied de la fente) ; son_pince (fichier audio) ; seuils_csv (fichier du module
Seuils) ; date ; source.

Une case vide = pas encore mesuré : l'importeur met une valeur NOMINALE et la marque
`a_mesurer: true` dans le yaml. Une valeur suivie de `?` (`la3?`, `0,6?`) est une
estimation : elle est utilisée, mais reste marquée `a_mesurer: true`. Rien n'est inventé
en silence.
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import math
import os
import re
import unicodedata
from dataclasses import dataclass, field

from .languette import MATERIAUX, Languette, Troncon, euler_bernoulli, materiau

COL_TRONCON = ["longueur_mm", "largeur_debut_mm", "largeur_fin_mm", "epaisseur_debut_mm",
               "epaisseur_fin_mm", "materiau"]
COL_ANCHE = ["instrument", "rang", "note", "sens", "position", "chambre", "levee_mm",
             "fente_longueur_mm", "fente_largeur_mm", "plaque_mm", "masse_bout", "rivet_mm",
             "son_pince", "seuils_csv", "date", "source"]
EN_TETE = ["type", "id"] + COL_TRONCON + COL_ANCHE

# Bornes « pas absurdes » (mm, g, Hz). Hors bornes : erreur ; en limite : attention.
BORNES = {
    "longueur_mm": (0.1, 150.0), "largeur_mm": (0.3, 20.0), "epaisseur_mm": (0.02, 5.0),
    "L_totale_mm": (5.0, 150.0), "levee_mm": (0.0, 5.0), "fente_longueur_mm": (5.0, 160.0),
    "fente_largeur_mm": (0.3, 21.0), "plaque_mm": (0.3, 6.0), "rivet_mm": (0.5, 30.0),
    "masse_bout_g": (0.001, 30.0), "note_Hz": (16.0, 8000.0), "chambre": (1, 80),
}


# --- Petits outils ---------------------------------------------------------------------------
def _sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").lower().strip()


def _nombre(texte):
    """'4,55' ou '4.55' -> 4.55 ; vide -> None ; sinon ValueError."""
    t = str(texte).strip().replace(" ", "").replace("\u00a0", "")
    if t == "":
        return None
    return float(t.replace(",", "."))


NOMS_FR = {"do": 0, "re": 2, "mi": 4, "fa": 5, "sol": 7, "la": 9, "si": 11}
NOMS_EN = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
NOMS_SORTIE = ["do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#", "la", "la#", "si"]


def note_hz(texte, la=440.0):
    """Une note en Hz. 'la3' (français, la3 = 440 Hz), 'sib2', 'do#4', 'A4' (anglais,
    A4 = 440 Hz), ou un nombre ('440', '440 Hz'). Renvoie None si vide."""
    t = _sans_accents(texte).replace(" ", "")
    if t == "":
        return None
    m = re.fullmatch(r"([\d.,]+)(hz)?", t)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.fullmatch(r"(do|re|mi|fa|sol|la|si)(#|b|d|diese|bemol)?(-?\d)", t)
    if m:
        demi = NOMS_FR[m.group(1)] + {"#": 1, "d": 1, "diese": 1, "b": -1, "bemol": -1}.get(m.group(2) or "", 0)
        midi = 12 * (int(m.group(3)) + 2) + demi            # la3 -> 69
        return la * 2 ** ((midi - 69) / 12)
    m = re.fullmatch(r"([a-g])(#|b)?(-?\d)", t)
    if m:
        demi = NOMS_EN[m.group(1)] + {"#": 1, "b": -1}.get(m.group(2) or "", 0)
        midi = 12 * (int(m.group(3)) + 1) + demi            # A4 -> 69
        return la * 2 ** ((midi - 69) / 12)
    raise ValueError(f"note illisible : {texte!r} (exemples : la3, sib2, do#4, A4, 440)")


def nom_note(f, la=440.0):
    """(nom français, écart en cents) de la note la plus proche (la3 = 440 Hz)."""
    m = 69 + 12 * math.log2(f / la)
    n = round(m)
    return f"{NOMS_SORTIE[n % 12]}{n // 12 - 2}", 100 * (m - n)


@dataclass
class Probleme:
    niveau: str          # "erreur" ou "attention"
    ligne: int
    message: str

    def __str__(self):
        return f"ligne {self.ligne} : {self.niveau.upper()} : {self.message}"


@dataclass
class Anche:
    """Une anche de la banque, telle que le yaml la porte.

    `champs[nom] = {"valeur": ..., "a_mesurer": bool}` ; `troncons` : liste de dicts
    (longueur_mm, largeur_mm [début, fin], epaisseur_mm [début, fin], materiau)."""
    id: str
    champs: dict = field(default_factory=dict)
    troncons: list = field(default_factory=list)
    troncons_a_mesurer: bool = False
    troncons_source: str = ""

    def valeur(self, nom, defaut=None):
        v = self.champs.get(nom, {}).get("valeur")
        return defaut if v is None else v

    def a_mesurer(self, nom):
        return bool(self.champs.get(nom, {}).get("a_mesurer", True))

    def liste_a_mesurer(self):
        out = [k for k, v in self.champs.items() if v.get("a_mesurer")]
        if self.troncons_a_mesurer:
            out.insert(0, "troncons")
        return out

    def languette(self, facteur_epaisseur=1.0, E=None):
        """La languette (SI). `facteur_epaisseur` et `E` servent au recalage."""
        tr = [Troncon(t["longueur_mm"] * 1e-3, tuple(b * 1e-3 for b in t["largeur_mm"]),
                      tuple(e * 1e-3 * facteur_epaisseur for e in t["epaisseur_mm"]),
                      t.get("materiau", "acier"),
                      E=E if (E is not None and t.get("materiau", "acier") == "acier") else None)
              for t in self.troncons]
        masses = []
        mb = self.valeur("masse_bout")
        if isinstance(mb, (int, float)) and not isinstance(mb, bool) and mb > 0:
            L = sum(t.longueur for t in tr)
            masses.append((L - 1e-3, mb * 1e-3))           # centrée à 1 mm du bout
        return Languette(tr, masses, nom=self.id)


# --- Lecture du CSV --------------------------------------------------------------------------
def _lire_lignes(chemin_ou_texte):
    if os.path.exists(str(chemin_ou_texte)):
        with open(chemin_ou_texte, encoding="utf-8-sig") as fh:
            texte = fh.read()
    else:
        texte = str(chemin_ou_texte)
    lignes = texte.splitlines()
    en_tete = next((l for l in lignes if l.strip() and not l.lstrip().startswith("#")), "")
    sep = ";" if ";" in en_tete else ("\t" if "\t" in en_tete else ",")
    return list(csv.reader(io.StringIO(texte), delimiter=sep)), sep


def importer(chemin_ou_texte, dossier=None):
    """Lit la banque. Renvoie `(anches, problemes)`. Une anche avec une erreur est
    quand même rendue (pour la voir), mais `problemes` le dit : ne pas calculer avec."""
    rangs, sep = _lire_lignes(chemin_ou_texte)
    dossier = dossier or (os.path.dirname(os.path.abspath(chemin_ou_texte))
                          if os.path.exists(str(chemin_ou_texte)) else os.getcwd())
    pb = []
    cols = None
    brut = {}                     # id -> {"ligne": n, "anche": dict, "troncons": [(n, dict)]}
    ordre = []
    courant = None
    for n, r in enumerate(rangs, start=1):
        if not r or all(not c.strip() for c in r) or r[0].lstrip().startswith("#"):
            continue
        if cols is None:
            cols = [_sans_accents(c) for c in r]
            manque = [c for c in ("type", "id") if c not in cols]
            if manque:
                pb.append(Probleme("erreur", n, f"en-tête sans les colonnes {manque} : {EN_TETE}"))
                return [], pb
            inconnues = [c for c in cols if c and c not in EN_TETE]
            if inconnues:
                pb.append(Probleme("attention", n, f"colonnes inconnues ignorées : {inconnues}"))
            continue
        d = {c: (r[i].strip() if i < len(r) else "") for i, c in enumerate(cols)}
        typ = _sans_accents(d.get("type", ""))
        if typ == "anche":
            ident = d.get("id", "")
            if not ident:
                pb.append(Probleme("erreur", n, "une anche sans id"))
                continue
            if ident in brut:
                pb.append(Probleme("erreur", n, f"id en double : {ident}"))
                continue
            brut[ident] = {"ligne": n, "anche": d, "troncons": []}
            ordre.append(ident)
            courant = ident
        elif typ in ("troncon", "tronçon"):
            ident = d.get("id") or courant
            if ident not in brut:
                pb.append(Probleme("erreur", n, f"tronçon sans anche (id {ident!r}) : mettre la ligne « anche » avant"))
                continue
            brut[ident]["troncons"].append((n, d))
        else:
            pb.append(Probleme("erreur", n, f"type inconnu {d.get('type')!r} : « anche » ou « troncon »"))
    return [_construire(i, brut[i], dossier, pb) for i in ordre], pb


def _champ(valeur, a_mesurer, estime=False):
    return {"valeur": valeur, "a_mesurer": bool(a_mesurer)}


def _verifier_nombre(nom, v, n, pb, borne=None, indice=""):
    lo, hi = BORNES[borne or nom]
    if v < lo or v > hi:
        aide = ""
        if (borne or nom).endswith("_mm") and v < lo and v > 0 and v * 1000 >= lo:
            aide = " (on dirait des mètres : écrire en mm)"
        elif (borne or nom) == "epaisseur_mm" and v > hi:
            aide = " (on dirait des centièmes de mm : 0,35 mm s'écrit 0,35)"
        pb.append(Probleme("erreur", n, f"{nom}{indice} = {v} hors de [{lo} ; {hi}]{aide}"))
        return False
    return True


def _construire(ident, b, dossier, pb):
    n0 = b["ligne"]
    d = dict(b["anche"])
    estime = set()                       # valeurs suivies de « ? » : utilisées, mais à mesurer
    for k in COL_ANCHE:
        v = d.get(k, "").strip()
        if v.endswith("?"):
            d[k] = v[:-1].strip()
            estime.add(k)
    a = Anche(id=ident)
    # -- tronçons
    for n, t in b["troncons"]:
        try:
            L = _nombre(t.get("longueur_mm", ""))
            b0 = _nombre(t.get("largeur_debut_mm", ""))
            b1 = _nombre(t.get("largeur_fin_mm", "")) if t.get("largeur_fin_mm", "").strip() else b0
            e0 = _nombre(t.get("epaisseur_debut_mm", ""))
            e1 = _nombre(t.get("epaisseur_fin_mm", "")) if t.get("epaisseur_fin_mm", "").strip() else e0
        except ValueError as ex:
            pb.append(Probleme("erreur", n, f"nombre illisible : {ex}"))
            continue
        if None in (L, b0, e0):
            pb.append(Probleme("erreur", n, "un tronçon demande au moins longueur, largeur et épaisseur"))
            continue
        ok = _verifier_nombre("longueur_mm", L, n, pb)
        for v, ind in ((b0, " (début)"), (b1, " (fin)")):
            ok &= _verifier_nombre("largeur_mm", v, n, pb, indice=ind)
        for v, ind in ((e0, " (début)"), (e1, " (fin)")):
            ok &= _verifier_nombre("epaisseur_mm", v, n, pb, indice=ind)
        mat = _sans_accents(t.get("materiau", "") or "acier")
        try:
            materiau(mat)
        except ValueError as ex:
            pb.append(Probleme("erreur", n, str(ex)))
            ok = False
        if ok and max(e0, e1) > max(b0, b1):
            pb.append(Probleme("attention", n, "épaisseur plus grande que la largeur : vérifier"))
        if ok:
            a.troncons.append(dict(longueur_mm=L, largeur_mm=[b0, b1], epaisseur_mm=[e0, e1], materiau=mat))
    # -- note
    f_note = None
    try:
        f_note = note_hz(d.get("note", ""))
        if f_note is not None:
            _verifier_nombre("note", f_note, n0, pb, borne="note_Hz")
    except ValueError as ex:
        pb.append(Probleme("erreur", n0, str(ex)))
    # -- tronçons nominaux si aucun
    if not a.troncons:
        a.troncons_a_mesurer = True
        a.troncons_source = "nominal : lame d'acier uniforme 0,30 x 3,5 mm accordée sur la note (à mesurer)"
        f = f_note or 440.0
        t, w = 0.3, 3.5
        L = math.sqrt(0.5596 * t * 1e-3 * math.sqrt(2.1e11 / (12 * 7800)) / f) * 1e3
        a.troncons.append(dict(longueur_mm=round(L, 2), largeur_mm=[w, w], epaisseur_mm=[t, t], materiau="acier"))
        if f_note is None:
            pb.append(Probleme("attention", n0, "ni tronçons ni note : lame nominale de 440 Hz"))
    else:
        a.troncons_source = d.get("source", "") or "banque"
    L_tot = sum(t["longueur_mm"] for t in a.troncons)
    _verifier_nombre("L_totale_mm", L_tot, n0, pb)
    b_max = max(max(t["largeur_mm"]) for t in a.troncons)
    b_bout = a.troncons[-1]["largeur_mm"][1]
    longueurs = [t["longueur_mm"] for t in a.troncons]
    ep = sorted((0.5 * sum(t["epaisseur_mm"]), t["longueur_mm"]) for t in a.troncons)
    cumul, e_med = 0.0, ep[0][0]
    for e, l in ep:
        cumul += l
        if cumul >= 0.5 * sum(longueurs):
            e_med = e
            break
    # -- champs simples (texte)
    for nom in ("instrument", "rang", "date", "source"):
        v = d.get(nom, "").strip()
        a.champs[nom] = _champ(v or None, (not v and nom in ("instrument", "rang")) or nom in estime)
    # -- note (nominale : f1 d'Euler-Bernoulli)
    if f_note is not None:
        a.champs["note"] = _champ(d.get("note").strip(), "note" in estime)
        a.champs["note_Hz"] = _champ(round(f_note, 3), "note" in estime)
    else:
        f1 = float(euler_bernoulli(a.languette(), 1)[0])
        nm, ct = nom_note(f1)
        a.champs["note"] = _champ(nm, True)
        a.champs["note_Hz"] = _champ(round(f1, 3), True)
        pb.append(Probleme("attention", n0, f"note non donnée : nominale {nm} ({f1:.1f} Hz, f1 calculée)"))
    # -- sens, position
    s = _sans_accents(d.get("sens", ""))
    sens = {"pousse": "pousse", "pousser": "pousse", "poussee": "pousse", "tire": "tire", "tirer": "tire",
            "tiree": "tire"}.get(s)
    if s and sens is None:
        pb.append(Probleme("erreur", n0, f"sens {d.get('sens')!r} : « pousse » ou « tire »"))
    a.champs["sens"] = _champ(sens, sens is None or "sens" in estime)
    p = _sans_accents(d.get("position", ""))
    pos = {"interieure": "interieure", "int": "interieure", "dedans": "interieure",
           "exterieure": "exterieure", "ext": "exterieure", "dehors": "exterieure"}.get(p)
    if p and pos is None:
        pb.append(Probleme("erreur", n0, f"position {d.get('position')!r} : « interieure » ou « exterieure »"))
    a.champs["position"] = _champ(pos, pos is None or "position" in estime)
    if sens and pos and {("pousse", "exterieure"), ("tire", "interieure")}.isdisjoint({(sens, pos)}):
        pb.append(Probleme("attention", n0, f"{sens} et {pos} : d'habitude l'anche extérieure sonne en "
                                            "poussé et l'intérieure en tiré ; vérifier"))
    # -- nombres, avec leurs valeurs nominales
    nominaux = {
        "levee_mm": round(1.5 * e_med, 3),                       # règle de coupled_reeds.steel_reed
        "fente_longueur_mm": round(L_tot + 0.03, 3),
        "fente_largeur_mm": round(b_max + 0.06, 3),               # jeu nominal 30 um de chaque côté
        "plaque_mm": round(max(0.8, 3 * e_med), 3),
        "rivet_mm": 3.0,
        "chambre": None,
    }
    for nom, nominal in nominaux.items():
        brut = d.get(nom, "").strip()
        try:
            v = _nombre(brut)
        except ValueError:
            pb.append(Probleme("erreur", n0, f"{nom} illisible : {brut!r}"))
            v = None
        if v is not None:
            if nom == "chambre":
                v = int(round(v))
            _verifier_nombre(nom, v, n0, pb)
            a.champs[nom] = _champ(v, nom in estime)
        else:
            a.champs[nom] = _champ(nominal, True)
    lev = a.valeur("levee_mm")
    if lev is not None and lev > 0.5 * L_tot:
        pb.append(Probleme("attention", n0, f"levée {lev} mm : plus de la moitié de la longueur ?"))
    if not a.a_mesurer("fente_largeur_mm") and a.valeur("fente_largeur_mm") < b_bout:
        pb.append(Probleme("attention", n0, "la languette est plus large que sa fente au bout : vérifier"))
    if not a.a_mesurer("fente_longueur_mm") and a.valeur("fente_longueur_mm") < L_tot:
        pb.append(Probleme("attention", n0, "fente plus courte que la languette : vérifier la longueur libre"))
    # -- masse au bout
    mb = _sans_accents(d.get("masse_bout", ""))
    if mb in ("", "?"):
        a.champs["masse_bout"] = _champ(None, True)
    elif mb in ("non", "0", "aucune"):
        a.champs["masse_bout"] = _champ("non", "masse_bout" in estime)
    elif mb in ("oui", "o"):
        a.champs["masse_bout"] = _champ("oui", "masse_bout" in estime)
        if not b["troncons"] or a.troncons[-1]["epaisseur_mm"][1] < 2.0 * e_med:
            pb.append(Probleme("attention", n0, "masse au bout « oui », mais aucun tronçon épais au bout : "
                                                "la décrire en tronçon (laiton...) ou donner sa masse en g"))
    else:
        try:
            g = _nombre(mb.replace("g", ""))
            _verifier_nombre("masse_bout", g, n0, pb, borne="masse_bout_g")
            a.champs["masse_bout"] = _champ(g, "masse_bout" in estime)
        except ValueError:
            pb.append(Probleme("erreur", n0, f"masse_bout {d.get('masse_bout')!r} : non, oui, ou un nombre de g"))
            a.champs["masse_bout"] = _champ(None, True)
    # -- fichiers
    for nom in ("son_pince", "seuils_csv"):
        v = d.get(nom, "").strip()
        if v:
            chemin = v if os.path.isabs(v) else os.path.join(dossier, v)
            if not os.path.exists(chemin):
                pb.append(Probleme("attention", n0, f"{nom} : fichier introuvable ({chemin})"))
            a.champs[nom] = _champ(v, False)
        else:
            a.champs[nom] = _champ(None, True)
    for k in estime:                     # pour réécrire « la3? » tel quel dans le CSV
        if k in a.champs and a.champs[k].get("valeur") is not None:
            a.champs[k]["estime"] = True
    return a


# --- Écriture du CSV (reedgui) ---------------------------------------------------------------
def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    return str(v)


def ecrire_banque(anches, chemin):
    """Écrit la banque (séparateur `;`, virgule décimale). Les valeurs encore
    `a_mesurer` sont écrites vides : elles redeviendront nominales à l'import."""
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(EN_TETE)
        for a in anches:
            ligne = {"type": "anche", "id": a.id}
            for k in COL_ANCHE:
                c = a.champs.get(k)
                if c is None or c.get("valeur") is None:
                    ligne[k] = ""
                elif c.get("a_mesurer"):
                    # une valeur à mesurer venue du CSV (estimation) garde son « ? » ;
                    # une nominale calculée par l'importeur repart vide
                    ligne[k] = _fmt(c.get("valeur")) + "?" if c.get("estime") else ""
                else:
                    ligne[k] = _fmt(c.get("valeur"))
            w.writerow([ligne.get(c, "") for c in EN_TETE])
            if a.troncons_a_mesurer:
                continue
            for t in a.troncons:
                lt = {"type": "troncon", "id": a.id, "longueur_mm": _fmt(float(t["longueur_mm"])),
                      "largeur_debut_mm": _fmt(float(t["largeur_mm"][0])),
                      "largeur_fin_mm": _fmt(float(t["largeur_mm"][1])),
                      "epaisseur_debut_mm": _fmt(float(t["epaisseur_mm"][0])),
                      "epaisseur_fin_mm": _fmt(float(t["epaisseur_mm"][1])),
                      "materiau": t.get("materiau", "acier")}
                w.writerow([lt.get(c, "") for c in EN_TETE])


# --- Le yaml du modèle -----------------------------------------------------------------------
def ecrire_yaml(anches, chemin, source_csv=""):
    import yaml
    doc = {
        "version": 1,
        "genere_le": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_csv": os.path.basename(source_csv) if source_csv else "",
        "unites": "longueurs en mm, masses en g, fréquences en Hz ; la3 = 440 Hz",
        "materiaux": {k: {"E_GPa": v["E"] / 1e9, "rho_kg_m3": v["rho"], "nu": v["nu"]} for k, v in MATERIAUX.items()},
        "anches": [],
    }
    for a in anches:
        lang = a.languette()
        f1 = float(euler_bernoulli(lang, 1)[0])
        doc["anches"].append({
            "id": a.id,
            "a_mesurer": a.liste_a_mesurer(),
            **{k: v for k, v in a.champs.items()},
            "troncons": {"a_mesurer": a.troncons_a_mesurer, "source": a.troncons_source,
                         "liste": a.troncons},
            "calcule": {"L_libre_mm": round(lang.L * 1e3, 3), "masse_libre_g": round(lang.masse() * 1e3, 4),
                        "f1_euler_bernoulli_Hz": round(f1, 2),
                        "note_f1": "%s %+.0f c" % nom_note(f1)},
        })
    entete = ("# PRODUIT par banc_recherche/banque_anches.py depuis la banque CSV : ne pas modifier\n"
              "# à la main. Modifier le CSV, puis relancer :\n"
              "#   J:\\claude\\venv\\Scripts\\python.exe -m banc_recherche.banque_anches <banque.csv> --yaml <ce fichier>\n"
              "# a_mesurer: true = valeur NOMINALE (devinée), à remplacer par une mesure.\n")
    with open(chemin, "w", encoding="utf-8") as fh:
        fh.write(entete)
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=None, width=110)
    return chemin


def charger_yaml(chemin):
    """Les anches du yaml produit (liste d'`Anche`)."""
    import yaml
    with open(chemin, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    out = []
    for d in doc.get("anches", []):
        tr = d.get("troncons", {})
        champs = {k: v for k, v in d.items() if isinstance(v, dict) and "valeur" in v}
        out.append(Anche(id=d["id"], champs=champs, troncons=tr.get("liste", []),
                         troncons_a_mesurer=bool(tr.get("a_mesurer")), troncons_source=tr.get("source", "")))
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Importer la banque d'anches (CSV) et produire le yaml du modèle.")
    ap.add_argument("csv")
    ap.add_argument("--yaml", help="yaml à écrire (défaut : rien, contrôle seulement)")
    a = ap.parse_args(argv)
    anches, pb = importer(a.csv)
    for p in pb:
        print(p)
    erreurs = [p for p in pb if p.niveau == "erreur"]
    print(f"{len(anches)} anche(s), {len(erreurs)} erreur(s), {len(pb) - len(erreurs)} attention(s)")
    for an in anches:
        print(f"  {an.id} : à mesurer -> {', '.join(an.liste_a_mesurer()) or 'rien'}")
    if a.yaml:
        if erreurs:
            print("yaml NON écrit : corriger les erreurs d'abord")
            return 1
        print("->", ecrire_yaml(anches, a.yaml, a.csv))
    return 1 if erreurs else 0


if __name__ == "__main__":
    raise SystemExit(main())
