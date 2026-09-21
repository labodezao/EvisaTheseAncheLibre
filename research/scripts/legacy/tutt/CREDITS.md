# TUTT 4.1 — sources d'origine, et à qui elles appartiennent

Ce dossier contient les sources Fortran de **TUTT**, le logiciel de calcul de
perce que **B.B. « Ninob »** a écrit et développé sur plusieurs décennies, et
qu'il a transmis à Ewen au fil de dix ans de mentorat. Ce n'est pas notre
travail : c'est le sien, et il faut que ce soit dit clairement, une fois pour
toutes, dans le fichier que quiconque ouvre ce dossier lira en premier.

## Ce qui est ici et pourquoi

Ewen a demandé que tout entre dans le dépôt — ses perces comme les sources
qui les calculent — et que l'attribution soit explicite plutôt que diluée
dans un historique Git. Ce fichier fait ce travail.

Récupérées depuis le Google Drive d'Ewen, dossier « TUTT 4.1 les sources » :
22 sous-programmes Fortran, du calcul de la ligne de transfert conique
(`Ltran9.for`) aux corrections de longueur d'embouchure (`Lczbe.for`, `LCZB`
dans `Lczb2.for`), en passant par les pertes visco-thermiques de Kirchhoff
(`Propag4.for`) et le critère de résonance anche-tuyau (`Librt2.for`,
`Anche5.for`). La liste complète, fichier par fichier, est le sujet du
`README.md` de ce dossier.

## Ce que `banc_recherche/tutt.py` en a fait

Le module Python `banc_recherche/tutt.py` de ce dépôt est une **traduction**,
pas une copie : chaque formule y est reproduite depuis ces sources, avec sa
dérivation expliquée en commentaire et une référence à la subroutine
d'origine. Le lien entre les deux est documenté dans
`research/docs/modele_hybride_generalise.md` (§9 et §10), qui raconte
comment chaque pièce du modèle a été retrouvée ici — le tronçon conique
exact dans `Ltran9.for`, la correction de cheminée de Nederveen dans
`Lczb2.for`, le critère de résonance `Im(Z) = 0` dans les commentaires de
`Ltran9.for`.

Ce module a été validé en confrontant ses résultats à ceux que TUTT
lui-même a produits pour un fichier de référence (`tutt25.dat`, un traverso
baroque, avec sa sortie `justess.out`) — voir le §10 du même document pour
les chiffres.

## Licence et droits

TUTT n'a jamais été publié sous une licence libre ; c'est le logiciel privé
d'un chercheur, partagé de main à main dans une communauté de facteurs
d'instruments. Ces sources sont versionnées ici avec l'accord explicite
d'Ewen (le dépositaire de longue date de ces fichiers), pour la
reproductibilité de la thèse et parce que la traduction Python qui s'en
inspire ne peut se comprendre sans elles. Elles restent la propriété
intellectuelle de B.B. — s'il souhaite un jour qu'elles soient retirées ou
republiées autrement, cette demande prévaut sur tout ce qui est écrit ici.
