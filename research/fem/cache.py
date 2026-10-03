"""Un cache de calculs : ne pas refaire un calcul Elmer dont les entrées n'ont pas changé.

La clé est l'empreinte (SHA-1) des entrées (cotes, finesse du maillage, options), de
la version d'Elmer et de `SCHEMA` (à monter quand un script change sa façon de
calculer). Le résultat (JSON) est rangé dans `J:\\claude\\calculs\\cache\\`.
Pour tout recalculer : `CACHE_FEM=0` dans l'environnement, ou vider ce dossier.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import numpy as np

from elmer_outils import CALCULS

DOSSIER = os.path.join(CALCULS, "cache")
SCHEMA = 2


def _normal(o):
    """Entrées rendues stables pour l'empreinte (flottants à 10 chiffres)."""
    if isinstance(o, dict):
        return {str(k): _normal(v) for k, v in sorted(o.items(), key=lambda kv: str(kv[0]))}
    if isinstance(o, (list, tuple)):
        return [_normal(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(f"{float(o):.10g}")
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def cle(nom, entrees):
    texte = json.dumps({"nom": nom, "schema": SCHEMA, "entrees": _normal(entrees)}, sort_keys=True)
    return hashlib.sha1(texte.encode("utf-8")).hexdigest()[:16]


def _json(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if hasattr(o, "__dict__"):
        return o.__dict__
    raise TypeError(type(o))


def en_cache(nom, entrees, calcul):
    """Résultat de `calcul()` (un dict sérialisable), lu dans le cache s'il existe."""
    chemin = os.path.join(DOSSIER, f"{nom}_{cle(nom, entrees)}.json")
    if os.environ.get("CACHE_FEM", "1") != "0" and os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fh:
            d = json.load(fh)
        d["_cache"] = "lu"
        return d
    t0 = time.time()
    d = calcul()
    d["_duree_calcul_s"] = round(time.time() - t0, 2)
    os.makedirs(DOSSIER, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(dict(d, _entrees=_normal(entrees)), fh, default=_json, ensure_ascii=False)
    d["_cache"] = "calculé"
    return d
