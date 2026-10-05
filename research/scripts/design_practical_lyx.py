#!/usr/bin/env python3
"""design_practical : le livre de la fabrication, pièce par pièce, Markdown -> LyX 2.3 (format 544).

    python research/scripts/design_practical_lyx.py

Sources (seules à modifier) : research/docs/design_practical/NN_piece_{en,fr}.md, dans l'ordre
des numéros (00 introduction, 01 clavier main droite, 02a/02b main gauche, 03 soupapes et fuites,
04 soufflet, 05 sommiers, 06 anches, 07 registres, 08 caisse, 09 diagnostic). Chaque pièce :
théorie, analyse, outils de conception, réparation (partage voulu par Ewen le 05/10/2026 :
design_theory = l'acoustique, design_practical = la fabrication et la réparation).
Produit :
  - research/docs/design_practical.lyx (anglais, la thèse) : en-tête et annexe gardés, tout le
    corps entre les deux reconstruit depuis les sources ;
  - research/docs/design_practical_fr.lyx : la même chose en français, document autonome.
Les deux .lyx restent en CRLF, comme dans le dépôt.

Markdown accepté : # Partie, ## Chapitre, ### Section, #### Sous-section ; paragraphes ; listes
« - » et « 1. » ; **gras**, *italique* ; $formule$ et $$formule$$ ; tableaux à barres précédés
d'une ligne « Table: légende {#tab:nom} » ; figures « ![légende](figures/x.png){#fig:nom} » ;
renvois « @tab:nom », « @fig:nom » ; paragraphe commençant par « > » = encart en italique.
Les chiffres se recalculent avec research/scripts/outils_atelier.py ; ceux de la main gauche
viennent de J:/zw3d_travail/librt/theorie (rapport.md, calcul_mecanique.py).
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(ICI, "..", "docs"))
SRC = os.path.join(DOCS, "design_practical")
BS = "\\"

TITRE_THEORIE = "Conceptual accordion design : Theory"  # titre copié de design_theory
TITRES = {"en": "Conceptual accordion design : Practice", "fr": "Conception d'accordéons : la pratique"}


# ------------------------------------------------------------- en ligne ---

# Caractères que pdflatex (inputenc utf8) ne sait pas écrire en ERT brut : traduits en LaTeX.
SYMBOLES = {"×": "$\\times$", "²": "$^{2}$", "³": "$^{3}$", "µ": "$\\mu$", "μ": "$\\mu$",
            "Δ": "$\\Delta$", "η": "$\\eta$", "−": "$-$", "÷": "$\\div$", "≤": "$\\le$",
            "≥": "$\\ge$", "≈": "$\\approx$", "°": "$^{\\circ}$", "€": "EUR", "→": "$\\to$",
            "±": "$\\pm$", "·": "$\\cdot$", "…": "\\dots{}", "–": "--", "—": "---"}


def echapper_ert(t):
    t = (t.replace("\\", "\\textbackslash{}").replace("%", "\\%").replace("&", "\\&")
          .replace("#", "\\#").replace("_", "\\_").replace("$", "\\$"))
    for car, latex in SYMBOLES.items():  # après l'échappement du « $ », pour garder les formules
        t = t.replace(car, latex)
    return re.sub(r"\^(\d+)", r"$^{\1}$", t)  # 10^6 -> 10$^{6}$


GRECQUES = {"Δ": "\\Delta", "η": "\\eta", "µ": "\\mu", "μ": "\\mu"}  # pdflatex : en formule

LANGUE = "en"  # fixée par main() avant chaque document
MOTS_REF = {"en": {"tab": "Table", "fig": "Figure"}, "fr": {"tab": "tableau", "fig": "figure"}}


def mot_ref(avant, genre):
    """Le mot à mettre devant un numéro de renvoi (« Table 2.1 »), ou rien s'il y est déjà."""
    if re.search(r"(tables?|tableaux?|figures?|fig\.)\s*$", avant, re.I):
        return ""
    mot = MOTS_REF[LANGUE][genre]
    debut_phrase = not avant.strip() or avant.rstrip().endswith((".", "(", ":", "?", "!"))
    return (mot[0].upper() + mot[1:] if debut_phrase else mot) + " "


def inline(texte):
    """Texte d'un paragraphe -> lignes LyX (gras, italique, formules, renvois)."""
    # Lettres grecques hors formule -> petite formule (LyX les écrirait en \textgreek, sans police).
    morceaux = re.split(r"(\$[^$]+\$)", texte)
    texte = "".join(m if m.startswith("$") else
                    re.sub("[" + "".join(GRECQUES) + "]", lambda g: f"${GRECQUES[g.group(0)]}$", m)
                    for m in morceaux)
    out, pos = [], 0
    motif = re.compile(r"(\$[^$]+\$|\*\*[^*]+\*\*|\*[^*\s][^*]*\*|@(?:tab|fig):[\w-]+)")
    for m in motif.finditer(texte):
        if m.start() > pos:
            out.append(texte[pos:m.start()])
        tok = m.group(0)
        if tok.startswith("$"):
            out.append(f"\n{BS}begin_inset Formula {tok}\n{BS}end_inset\n")
        elif tok.startswith("**"):
            out.append(f"\n{BS}series bold\n{tok[2:-2]}\n{BS}series default\n")
        elif tok.startswith("*"):
            out.append(f"\n{BS}shape italic\n{tok[1:-1]}\n{BS}shape default\n")
        else:
            out.append(mot_ref(texte[:m.start()], tok[1:4]))
            out.append(f"\n{BS}begin_inset CommandInset ref\nLatexCommand ref\nreference \"{tok[1:]}\"\n"
                       f"plural \"false\"\ncaps \"false\"\nnoprefix \"false\"\n\n{BS}end_inset\n")
        pos = m.end()
    out.append(texte[pos:])
    return "".join(out)


def layout(nom, contenu):
    return f"{BS}begin_layout {nom}\n{contenu}\n{BS}end_layout\n\n"


# ------------------------------------------------------------- blocs ---

def tableau(lignes, legende, label):
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lignes
            if not re.match(r"^\s*\|?\s*:?-{2,}", l)]
    ncol = max(len(r) for r in rows)
    corps = []
    def ert(t):
        corps.append(f"{BS}begin_layout Plain Layout\n\n{t}\n{BS}end_layout\n\n")
    # Tableau de chiffres : colonnes « l ». Tableau de phrases : colonnes « p » sur la largeur
    # de la page, chacune selon la longueur de son texte le plus long.
    longueurs = [max(len(r[k]) if k < len(r) else 0 for r in rows) for k in range(ncol)]
    phrases = sum(longueurs) > 55
    if phrases:  # largeur utile moins les marges de colonnes (2 x 6 pt chacune)
        poids = [max(n, 8) for n in longueurs]
        total = 0.94 - 0.032 * ncol
        spec = "".join(f"p{{{total * p / sum(poids):.3f}{BS}linewidth}}" for p in poids)
    else:
        spec = "l" * ncol
    ert(f"{BS}backslash\nbegin{{tabular}}{{" + spec.replace(BS, f"\n{BS}backslash\n") + "}")
    ert(f"{BS}backslash\nhline")
    for i, r in enumerate(rows):
        cases = [echapper_ert(c.replace("**", "")) for c in r + [""] * (ncol - len(r))]
        if phrases:  # texte en drapeau ; \tabularnewline, car \\ ne finit plus la ligne après \raggedright
            cells = " & ".join(BS + "raggedright " + c for c in cases)
            ert(cells.replace(BS, f"\n{BS}backslash\n") + f" \n{BS}backslash\ntabularnewline")
        else:
            cells = " & ".join(cases)
            ert(cells.replace(BS, f"\n{BS}backslash\n") + f" \n{BS}backslash\n\n{BS}backslash\n")
        if i == 0:
            ert(f"{BS}backslash\nhline")
    ert(f"{BS}backslash\nhline")
    ert(f"{BS}backslash\nend{{tabular}}")
    lab = (f"{BS}begin_inset CommandInset label\nLatexCommand label\nname \"{label}\"\n\n{BS}end_inset\n\n"
           if label else "")
    return (f"{BS}begin_layout Standard\n{BS}begin_inset Float table\nwide false\nsideways false\nstatus open\n\n"
            f"{BS}begin_layout Plain Layout\n{BS}begin_inset Caption Standard\n\n{BS}begin_layout Plain Layout\n"
            f"{lab}{inline(legende)}\n{BS}end_layout\n\n{BS}end_inset\n\n\n{BS}end_layout\n\n"
            f"{BS}begin_layout Plain Layout\n{BS}align center\n{BS}size footnotesize\n"
            f"{BS}begin_inset ERT\nstatus open\n\n{''.join(corps)}{BS}end_inset\n\n\n{BS}end_layout\n\n"
            f"{BS}end_inset\n\n\n{BS}end_layout\n\n")


def figure(fichier, legende, label):
    lab = (f"{BS}begin_inset CommandInset label\nLatexCommand label\nname \"{label}\"\n\n{BS}end_inset\n\n"
           if label else "")
    return (f"{BS}begin_layout Standard\n{BS}begin_inset Float figure\nwide false\nsideways false\nstatus open\n\n"
            f"{BS}begin_layout Plain Layout\n{BS}align center\n{BS}begin_inset Graphics\n\tfilename {fichier}\n"
            f"\twidth 100text%\n\n{BS}end_inset\n\n\n{BS}end_layout\n\n"
            f"{BS}begin_layout Plain Layout\n{BS}begin_inset Caption Standard\n\n{BS}begin_layout Plain Layout\n"
            f"{lab}{inline(legende)}\n{BS}end_layout\n\n{BS}end_inset\n\n\n{BS}end_layout\n\n"
            f"{BS}end_inset\n\n\n{BS}end_layout\n\n")


def convertir(md):
    """Markdown -> corps LyX."""
    out, para = [], []
    lignes = md.split("\n")
    i = 0

    def vider():
        nonlocal para
        if para:
            texte = " ".join(para).strip()
            if texte.startswith(">"):
                out.append(layout("Standard", f"{BS}shape italic\n{inline(texte.lstrip('> ').strip())}"))
            else:
                out.append(layout("Standard", inline(texte)))
            para = []

    niveaux = {1: "Part", 2: "Chapter", 3: "Section", 4: "Subsection"}
    legende_tab = None
    while i < len(lignes):
        l = lignes[i]
        s = l.strip()
        m_tit = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m_tit:
            vider()
            out.append(layout(niveaux[len(m_tit.group(1))], inline(m_tit.group(2))))
        elif s.startswith("Table:"):
            vider()
            legende_tab = s[6:].strip()
        elif s.startswith("|"):
            vider()
            bloc = []
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                bloc.append(lignes[i]); i += 1
            leg, lab = legende_tab or "", None
            m = re.search(r"\{#(tab:[\w-]+)\}", leg)
            if m:
                lab = m.group(1); leg = leg[:m.start()].strip()
            out.append(tableau(bloc, leg, lab))
            legende_tab = None
            continue
        elif s.startswith("!["):
            vider()
            m = re.match(r"!\[(.*)\]\(([^)]+)\)(\{#(fig:[\w-]+)\})?", s)
            out.append(figure(m.group(2), m.group(1), m.group(4)))
        elif s.startswith("$$"):
            vider()
            f = s.strip("$")
            out.append(layout("Standard", f"{BS}begin_inset Formula \\[\n{f}\n\\]\n{BS}end_inset"))
        elif re.match(r"^(- |\d+\. )", s):
            vider()
            nom = "Itemize" if s.startswith("- ") else "Enumerate"
            texte = re.sub(r"^(- |\d+\. )", "", s)
            while i + 1 < len(lignes) and lignes[i + 1].startswith("  ") and lignes[i + 1].strip():
                i += 1; texte += " " + lignes[i].strip()
            out.append(layout(nom, inline(texte)))
        elif not s:
            vider()
        else:
            para.append(s)
        i += 1
    vider()
    return "".join(out)


# ------------------------------------------------------- documents ---

def sources(langue):
    """Les sources d'une langue, dans l'ordre des pièces (00_, 01_, 02a_, 02b_ ...)."""
    noms = sorted(n for n in os.listdir(SRC) if re.match(rf"^\d\d[a-z]?_.+_{langue}\.md$", n))
    textes = []
    for n in noms:
        with open(os.path.join(SRC, n), encoding="utf-8") as f:
            textes.append(f.read().strip())
    return noms, "\n\n".join(textes) + "\n"


def lire_lyx(nom):
    with open(os.path.join(DOCS, nom), encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def ecrire_lyx(nom, txt):
    """Le dépôt garde les .lyx en CRLF (sinon tout le fichier change)."""
    with open(os.path.join(DOCS, nom), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(txt)


def decouper(txt):
    """(en-tête jusqu'à la première partie, annexe et fin) de design_practical.lyx."""
    debut = txt.index(f"{BS}begin_body")
    tete = txt[:txt.index(f"{BS}begin_layout Part\n", debut)]
    queue = txt[txt.index(f"{BS}begin_layout Part\nAppendix"):]
    # Les chapitres vides « Leaks detection » de l'ancienne table : les fuites ont leur partie.
    queue = queue.replace(f"{BS}begin_layout Chapter\nLeaks detection\n{BS}end_layout\n\n", "")
    return tete, queue


def langue_de(tete, langue):
    langue_lyx = "french" if langue == "fr" else "english"
    return re.sub(r"\n\\language \w+", lambda m: f"\n{BS}language {langue_lyx}", tete)


def main():
    global LANGUE
    sys.stdout.reconfigure(encoding="utf-8")
    LANGUE = "en"
    tete, queue = decouper(lire_lyx("design_practical.lyx"))
    tete = tete.replace(TITRE_THEORIE, TITRES["en"])
    noms, md = sources("en")
    ecrire_lyx("design_practical.lyx", tete + convertir(md) + queue)
    print("design_practical.lyx :", ", ".join(noms))
    # Version française autonome : même en-tête, sans l'annexe (feuille de route de la thèse).
    LANGUE = "fr"
    noms, md = sources("fr")
    if noms:
        biblio = queue.find(f"{BS}begin_layout Chapter*\nBibliography")
        fin = queue[biblio:] if biblio >= 0 else f"{BS}end_body\n{BS}end_document\n"
        tete_fr = langue_de(tete, "fr").replace(TITRES["en"], TITRES["fr"])
        ecrire_lyx("design_practical_fr.lyx", tete_fr + convertir(md) + fin)
        print("design_practical_fr.lyx :", ", ".join(noms))


if __name__ == "__main__":
    main()
