#!/usr/bin/env python3
"""Chapitre « mécanique main gauche » : Markdown -> LyX 2.3 (format 544), en français et en anglais.

    python research/scripts/mecanique_lyx.py

Sources (seules à modifier) : research/docs/mecanique_main_gauche/{theorie,pratique}_{fr,en}.md
Produit :
  - research/docs/mecanique_main_gauche_fr.lyx, ..._en.lyx : documents autonomes (théorie + pratique),
    même gabarit que design_theory.lyx (Legrand Orange Book), langue française ou anglaise ;
  - la partie anglaise « Left-hand mechanism » dans design_practical.lyx (avant « Appendix ») :
    chapitre de théorie, puis chapitres pratiques. design_theory.lyx n'est pas touché.
Relancer remplace les blocs déjà insérés (repérés par leur titre), sans les dupliquer.

Markdown accepté : # Partie, ## Chapitre, ### Section, #### Sous-section ; paragraphes ; listes
« - » et « 1. » ; **gras**, *italique* ; $formule$ et $$formule$$ ; tableaux à barres précédés
d'une ligne « Table: légende {#tab:nom} » ; figures « ![légende](figures/x.png){#fig:nom} » ;
renvois « @tab:nom », « @fig:nom » ; paragraphe commençant par « > » = encart en italique.
Les sources des chiffres : J:/zw3d_travail/librt/theorie (rapport.md, calcul_mecanique.py).
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(ICI, "..", "docs"))
SRC = os.path.join(DOCS, "mecanique_main_gauche")
BS = "\\"

TITRES = {  # titre du bloc inséré, pour le retrouver et le remplacer
    "pratique": "Left-hand mechanism",
}


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
    ert(f"{BS}backslash\nbegin{{tabular}}{{{'l' * ncol}}}")
    ert(f"{BS}backslash\nhline")
    for i, r in enumerate(rows):
        cells = " & ".join(echapper_ert(c.replace("**", "")) for c in r + [""] * (ncol - len(r)))
        ert(cells.replace("\\", f"\n{BS}backslash\n") + f" \n{BS}backslash\n\n{BS}backslash\n")
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
    out, para, liste = [], [], None
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

def lire(nom):
    with open(os.path.join(SRC, nom), encoding="utf-8") as f:
        return f.read()


def entete(langue):
    """En-tête de design_theory.lyx (même gabarit), langue adaptée, corps vidé."""
    with open(os.path.join(DOCS, "design_theory.lyx"), encoding="utf-8") as f:
        txt = f.read()
    tete = txt[:txt.index(f"{BS}begin_body") + len(f"{BS}begin_body")]
    langue_lyx = "french" if langue == "fr" else "english"
    tete = re.sub(r"\n\\language \w+", lambda m: f"\n{BS}language {langue_lyx}", tete)
    return tete


def autonome(langue):
    corps = convertir(lire(f"theorie_{langue}.md")) + convertir(lire(f"pratique_{langue}.md"))
    titre = ("Mécanique main gauche : ce que le doigt paie pour une soupape" if langue == "fr"
             else "The left-hand mechanism: what a finger pays for a pallet")
    # Le gabarit (Legrand Orange Book) exige une image de chapitre, posée comme dans la thèse.
    image = layout("Standard", f"{BS}begin_inset ERT\nstatus collapsed\n\n{BS}begin_layout Plain Layout\n\n"
                               f"{BS}backslash\nchapterimage{{chapter_head_2.pdf}}\n{BS}end_layout\n\n{BS}end_inset\n")
    doc = (entete(langue) + "\n\n" + layout("Title", titre) + image + corps +
           f"{BS}end_body\n{BS}end_document\n")
    chemin = os.path.join(DOCS, f"mecanique_main_gauche_{langue}.lyx")
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    return chemin


def retirer_bloc(txt, niveau, titre, fins):
    """Retire un bloc commençant par « \\begin_layout <niveau>\\n<titre> » jusqu'au prochain des fins."""
    debut = txt.find(f"{BS}begin_layout {niveau}\n{titre}\n")
    if debut < 0:
        return txt, -1
    suite = [txt.find(f"{BS}begin_layout {f}\n", debut + 10) for f in fins]
    suite = [s for s in suite if s > 0]
    fin = min(suite) if suite else txt.index(f"{BS}end_body")
    return txt[:debut] + txt[fin:], debut


def inserer(fichier, bloc, niveau, titre, fins, avant):
    chemin = os.path.join(DOCS, fichier)
    with open(chemin, "rb") as f:
        fin_ligne = "\r\n" if b"\r\n" in f.read(4096) else "\n"  # garder celle du dépôt
    with open(chemin, encoding="utf-8") as f:
        txt = f.read()
    txt, pos = retirer_bloc(txt, niveau, titre, fins)
    if pos < 0:
        pos = txt.index(avant)
    txt = txt[:pos] + bloc + txt[pos:]
    with open(chemin, "w", encoding="utf-8", newline=fin_ligne) as f:
        f.write(txt)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for langue in ("fr", "en"):
        print("Écrit :", autonome(langue))
    # Tout dans design_practical.lyx (choix d'Ewen, 05/10) : une partie « Left-hand mechanism »
    # avant « Appendix », qui ouvre sur le chapitre de théorie puis les chapitres pratiques.
    pratique = lire("pratique_en.md")
    coupe = pratique.index("\n## ")
    md = pratique[:coupe] + "\n\n" + lire("theorie_en.md") + "\n" + pratique[coupe:]
    inserer("design_practical.lyx", convertir(md), "Part", TITRES["pratique"],
            ["Part"], f"{BS}begin_layout Part\nAppendix")
    print("Inséré : design_practical.lyx (partie : théorie + pratique)")


if __name__ == "__main__":
    main()
