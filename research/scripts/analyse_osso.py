#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
ANALYSE ACOUSTIQUE COMPUTATIONNELLE — corpus OSSO
================================================================================

Script complet et reproductible de l'analyse présentée dans
`research/docs/analyse_acoustique_osso.md` (« Analyse acoustique
computationnelle de deux pièces du duo OSSO »).

Chaque fonction correspond à une section du document :

    section 3.1  ->  analyse_mid_side()
    section 3.2  ->  analyse_timbre()
    section 3.3  ->  analyse_resonances()        [Praat]
    section 3.4  ->  spectre_modulation()
    section 3.5  ->  correction_metrique()
    section 3.6  ->  regression_centroide()
    section 3.7  ->  estimation_tonalite()
    section 3.8  ->  analyse_dynamique()

--------------------------------------------------------------------------------
DÉPENDANCES
--------------------------------------------------------------------------------
    pip install -r ../requirements.txt          # (depuis research/scripts/)
    pip install -e "..[musique]"                # ou seulement l'extra « musique »

Versions utilisées pour l'étude :
    librosa 1.0.0 · praat-parselmouth 0.4.7 · numpy 2.4.4 · Python 3.12

Ce script est volontairement autonome : contrairement aux modules de
`banc_recherche/`, il ne mesure pas une anche au banc mais analyse des
enregistrements. Il n'est donc pas importé par le package et ne fait pas
partie de la suite de tests (qui tourne avec numpy seul).

--------------------------------------------------------------------------------
DONNÉES — NON FOURNIES (droits d'auteur)
--------------------------------------------------------------------------------
Les deux enregistrements analysés NE SONT PAS versionnés dans ce dépôt : ce
sont des œuvres diffusées commercialement. Aucun extrait sonore n'est reproduit
ici ; seuls des descripteurs acoustiques dérivés sont publiés.

Pour rejouer l'analyse, procure-toi les fichiers légalement :
  · achat sur la page Bandcamp du duo OSSO ;
  · ou autorisation écrite des ayants droit pour un usage de recherche.

Place-les ensuite sous les noms :
    track1.mp3   (Ordre étant — hanter-dro)
    track2.mp3   (Duderc'h — scottish)

dans le répertoire courant, ou dans le dossier passé à --data.

--------------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------------
    python3 analyse_osso.py                      # analyse complète, sortie texte
    python3 analyse_osso.py --data ~/audio/osso  # audio ailleurs que dans le cwd
    python3 analyse_osso.py --figures            # + figures PNG dans docs/figures/
    python3 analyse_osso.py --figures /tmp/fig   # + figures dans un autre dossier

================================================================================
"""

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call
from scipy import stats

warnings.filterwarnings('ignore')

# ==============================================================================
# CONFIGURATION
# ==============================================================================

PIECES = [
    ('track1.mp3', "Ordre étant (hanter-dro)"),
    ('track2.mp3', "Duderc'h (scottish)"),
]

SR_ANALYSE = 44100      # fréquence d'échantillonnage pour l'analyse spectrale
SR_PRAAT   = 22050      # Praat : rééchantillonnage (suivi de formants)
FADE_EXCLU = 15         # secondes exclues en fin de piste (fondus)

# Convention du dépôt : les figures du manuscrit vivent dans research/docs/figures/
FIGURES_DIR = Path(__file__).resolve().parents[1] / 'docs' / 'figures'


def separateur(titre, niveau=1):
    """Affichage structuré des sections."""
    c = '=' if niveau == 1 else '-'
    print('\n' + c * 78)
    print(titre)
    print(c * 78)


# ==============================================================================
# PRÉPARATION — décodage et décomposition mid/side
# ==============================================================================

def preparer(fichier, prefixe):
    """
    Décode en stéréo pleine bande et écrit les composantes mid/side sur disque.

    La décomposition mid/side sépare l'information commune aux deux canaux
    (mid, M = (L+R)/2) de l'information différentielle (side, S = (L-R)/2).
    Elle permet d'isoler les sources monophoniques centrées des sources
    spatialisées — cf. document, section 3.1.

    `prefixe` est un chemin (sans extension) : les intermédiaires _mid.wav et
    _side.wav sont écrits à côté des fichiers audio source.

    Retourne : (mid, side, sr)
    """
    y, sr = librosa.load(str(fichier), sr=SR_ANALYSE, mono=False)

    if y.ndim == 1:                      # fichier mono : side nul
        mid, side = y, np.zeros_like(y)
    else:
        mid  = (y[0] + y[1]) / 2
        side = (y[0] - y[1]) / 2

    sf.write(f'{prefixe}_mid.wav',  mid,  sr)
    sf.write(f'{prefixe}_side.wav', side, sr)
    return mid, side, sr


# ==============================================================================
# SECTION 3.1 — organisation stéréophonique
# ==============================================================================

BANDES = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000),
          (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]


def repartition_bandes(y, sr, n_fft=4096):
    """Pourcentage d'énergie spectrale par bande de fréquence."""
    S = np.abs(librosa.stft(y, n_fft=n_fft))
    f = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    total = S.sum() + 1e-12
    return {(lo, hi): 100 * S[(f >= lo) & (f < hi)].sum() / total
            for lo, hi in BANDES}


def analyse_mid_side(mid, side, sr):
    """
    Section 3.1 — distribution des rôles dans le champ stéréophonique.

    Résultat clé de l'étude : le rapport mid/side sous 60 Hz atteint 9,2 sur
    la première pièce, contre 0,76 dans la bande 1000-2000 Hz. L'extrême grave
    (basse monophonique) est centré, le médium (synthés) est spatialisé.
    """
    em, es = float(np.sum(mid ** 2)), float(np.sum(side ** 2))
    print(f"  Énergie   Mid {100*em/(em+es):.1f} %   Side {100*es/(em+es):.1f} %")

    rm = repartition_bandes(mid,  sr)
    rs = repartition_bandes(side, sr)

    print(f"\n  {'Bande (Hz)':<14}{'Mid %':>8}{'Side %':>9}{'M/S':>8}")
    for lo, hi in BANDES:
        ratio = rm[(lo, hi)] / rs[(lo, hi)] if rs[(lo, hi)] > 0 else float('inf')
        print(f"  {f'{lo}-{hi}':<14}{rm[(lo,hi)]:>8.1f}{rs[(lo,hi)]:>9.1f}{ratio:>8.2f}")

    return rm, rs


# ==============================================================================
# SECTION 3.2 — nature du timbre
# ==============================================================================

def analyse_timbre(y, sr):
    """
    Section 3.2 — mesures de bruit, de périodicité et d'étendue spectrale.

    La platitude spectrale (spectral flatness) est le rapport entre moyenne
    géométrique et moyenne arithmétique du spectre. Proche de 0 : signal
    tonal. Proche de 1 : bruit. Une saturation forte élève mécaniquement
    cette valeur en générant des composantes inharmoniques — son absence
    dans le corpus indique qu'aucune distorsion notable n'est appliquée.

    La séparation HPSS (harmonic/percussive source separation) isole les
    composantes stables en fréquence (harmoniques) des transitoires larges
    bande (percussives), par filtrage médian du spectrogramme.
    """
    flat = librosa.feature.spectral_flatness(y=y)[0]
    roll = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
    bw   = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]

    H, P = librosa.effects.hpss(y, margin=3.0)
    eh, ep = float(np.sum(H ** 2)), float(np.sum(P ** 2))

    print(f"  Platitude spectrale   moy {flat.mean():.4f}   p90 {np.percentile(flat,90):.4f}")
    print(f"  Rolloff 85 %          {roll.mean():.0f} Hz")
    print(f"  Largeur de bande      {bw.mean():.0f} Hz")
    print(f"  HPSS  harmonique {100*eh/(eh+ep):.1f} %   percussif {100*ep/(eh+ep):.1f} %")

    return dict(flatness=flat.mean(), rolloff=roll.mean(),
                bandwidth=bw.mean(), harmonic=100*eh/(eh+ep))


# ==============================================================================
# SECTION 3.3 — pics de résonance (Praat)
# ==============================================================================

def analyse_resonances(fichier_wav):
    """
    Section 3.3 — analyse Praat : harmonicité, intensité, maxima spectraux.

    ATTENTION MÉTHODOLOGIQUE (cf. document, 2.4)
    Praat est conçu pour l'analyse de la parole. Le suivi de formants suppose
    un modèle source-filtre à résonances vocaliques. Appliqué à un signal de
    synthèse polyphonique, il détecte des maxima spectraux qui ne sont PAS des
    formants au sens phonétique. Ces valeurs doivent être interprétées comme
    des pics de résonance attribuables au filtrage.

    De même, le HNR suppose une source quasi-périodique unique ; sur un
    mixage, il mesure la périodicité globale de la texture.
    """
    snd = parselmouth.Sound(str(fichier_wav)).resample(SR_PRAAT)

    hnr = call(snd, 'To Harmonicity (cc)', 0.01, 60, 0.1, 4.5)
    hnr_moy = call(hnr, 'Get mean', 0, 0)

    inten = call(snd, 'To Intensity', 60, 0.01, 'yes')
    i_moy = call(inten, 'Get mean',    0, 0, 'energy')
    i_min = call(inten, 'Get minimum', 0, 0, 'parabolic')
    i_max = call(inten, 'Get maximum', 0, 0, 'parabolic')

    fmt = call(snd, 'To Formant (burg)', 0.02, 4, 5000, 0.025, 50)

    print(f"  HNR moyen             {hnr_moy:.2f} dB")
    print(f"  Intensité             moy {i_moy:.1f} dB   plage {i_max-i_min:.1f} dB")
    resonances = []
    for n in (1, 2, 3):
        m  = call(fmt, 'Get mean',               n, 0, 0, 'hertz')
        sd = call(fmt, 'Get standard deviation', n, 0, 0, 'hertz')
        resonances.append(m)
        print(f"  R{n} (pic de résonance) {m:.0f} Hz  (σ = {sd:.0f})")

    return dict(hnr=hnr_moy, resonances=resonances)


# ==============================================================================
# SECTION 3.4 — spectre de modulation
# ==============================================================================

BANDES_MOD = [(20, 120, 'grave'), (120, 800, 'bas-médium'),
              (800, 3000, 'médium'), (3000, 10000, 'aigu')]


def spectre_modulation(y, sr, n_fft=2048, hop=256, fmin=0.3, fmax=15, n_pics=3):
    """
    Section 3.4 — RÉSULTAT PRINCIPAL DE L'ÉTUDE.

    Principe : on extrait l'enveloppe d'énergie dans une bande de fréquence,
    puis on lui applique une transformée de Fourier. Les pics obtenus sont les
    fréquences auxquelles l'amplitude de cette bande fluctue — autrement dit
    les fréquences de modulation (LFO, trémolo, pulsation rythmique).

    Sur le corpus, les pics tombent sur les subdivisions métriques avec une
    erreur de 0,1 à 0,3 %, ce qui démontre un verrouillage des modulations
    sur la grille métrique.

    Le calcul est mené séparément par bande, car des modulations différentes
    peuvent affecter le grave et l'aigu (filtrage, trémolo sélectif).
    """
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    f = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    fps = sr / hop

    resultats = {}
    for lo, hi, nom in BANDES_MOD:
        env = S[(f >= lo) & (f < hi)].sum(axis=0)
        env = env - env.mean()                       # retrait de la composante continue

        spec  = np.abs(np.fft.rfft(env * np.hanning(len(env))))
        freqs = np.fft.rfftfreq(len(env), 1 / fps)

        masque = (freqs > fmin) & (freqs < fmax)
        idx = np.argsort(spec[masque])[::-1][:n_pics]
        pics = np.unique(np.round(freqs[masque][idx], 2))[::-1]

        resultats[nom] = pics
        print(f"  {nom:<12} {', '.join(f'{p:.2f} Hz' for p in pics)}")

    return resultats


# ==============================================================================
# SECTION 3.5 — correction de l'octave métrique
# ==============================================================================

SUBDIVISIONS = {0.25: 'ronde', 0.333: 'blanche pointée', 0.5: 'blanche',
                1.0: 'noire', 2.0: 'croche', 4.0: 'double-croche'}


def correction_metrique(pics, bpm_candidats):
    """
    Section 3.5 — CONTRIBUTION MÉTHODOLOGIQUE.

    Les algorithmes de suivi de battement confondent fréquemment un niveau
    métrique avec son double ou sa moitié (erreur d'octave métrique). Sur
    *Duderc'h*, librosa estime 120,2 BPM ; les modulations donnent alors des
    rapports de 0,749 / 1,498 / 2,995 — une erreur systématique de 49,8 %.

    L'hypothèse de 90 BPM résout exactement la discordance (rapports 1/2/4).

    Cette fonction teste plusieurs tempos candidats et retourne celui qui
    minimise l'erreur d'alignement des pics sur les subdivisions métriques.
    Elle constitue un test indépendant de validation du niveau métrique.
    """
    meilleur, err_min = None, float('inf')

    for bpm in bpm_candidats:
        noire = bpm / 60
        erreurs = []
        for p in pics:
            r = p / noire
            cible = min(SUBDIVISIONS, key=lambda k: abs(k - r))
            erreurs.append(abs(r - cible) / cible)
        err = float(np.mean(erreurs))
        print(f"  {bpm:>7.1f} BPM  ->  erreur moyenne {100*err:>6.2f} %")
        if err < err_min:
            meilleur, err_min = bpm, err

    print(f"\n  Tempo retenu : {meilleur:.1f} BPM (erreur {100*err_min:.2f} %)")
    noire = meilleur / 60
    for p in pics:
        r = p / noire
        cible = min(SUBDIVISIONS, key=lambda k: abs(k - r))
        print(f"    {p:.2f} Hz = {r:.3f} × noire  ->  {SUBDIVISIONS[cible]}")

    return meilleur, err_min


# ==============================================================================
# SECTION 3.6 — régression du centroïde spectral
# ==============================================================================

def regression_centroide(y, sr, hop=2048, exclure_fin=FADE_EXCLU):
    """
    Section 3.6 — dramaturgie timbrale.

    Le centroïde spectral est le barycentre du spectre : il constitue un
    corrélat objectif de la brillance perçue, et suit l'ouverture d'un filtre
    passe-bas. Sa régression linéaire sur la durée quantifie la trajectoire
    timbrale de la pièce.

    Les dernières secondes sont exclues pour neutraliser les fondus de fin,
    qui produiraient une pente artificielle.

    Résultat : +5,17 Hz/s (R² = 0,298, p < 0,001) sur le hanter-dro,
    contre -0,33 Hz/s (n.s.) sur la scottish.
    """
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
    roll = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85,
                                            hop_length=hop)[0]
    t = np.arange(len(cent)) * hop / sr
    m = t < (t[-1] - exclure_fin)

    pente, ordo, r, p, _ = stats.linregress(t[m], cent[m])
    pente_r, _, r_r, _, _ = stats.linregress(t[m], roll[m])

    signif = "significatif" if p < 0.05 else "NON significatif"
    print(f"  Centroïde   {pente:+.2f} Hz/s   R² = {r**2:.3f}   p = {p:.2e}  ({signif})")
    print(f"              départ {ordo:.0f} Hz  ->  arrivée {ordo + pente*t[m][-1]:.0f} Hz")
    print(f"  Rolloff85   {pente_r:+.2f} Hz/s   R² = {r_r**2:.3f}")

    return dict(pente=pente, r2=r**2, p=p, depart=ordo, temps=t, centroide=cent)


# ==============================================================================
# SECTION 3.7 — estimation de tonalité
# ==============================================================================

# Profils de Krumhansl-Schmuckler (Krumhansl & Kessler 1982 ; Krumhansl 1990),
# établis par tests perceptifs — cf. docs/references.bib
KS_MAJEUR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                      2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINEUR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                      2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ['Do', 'Do#', 'Ré', 'Ré#', 'Mi', 'Fa',
         'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si']


def estimation_tonalite(y, sr):
    """
    Section 3.7 — tonalité et ambiguïté modale.

    Méthode : corrélation du profil chroma moyen avec les 24 profils de
    Krumhansl-Schmuckler (12 majeurs, 12 mineurs).

    LIMITE INTERPRÉTATIVE : ces profils ont été établis sur le répertoire
    tonal occidental. Sur le corpus, l'écart entre hypothèse majeure et
    mineure est très faible (0,032 et 0,057), ce qui suggère une organisation
    modale ne relevant ni de l'un ni de l'autre — résultat cohérent avec les
    modes documentés du répertoire breton.
    """
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)

    scores = []
    for r in range(12):
        for profil, mode in ((KS_MAJEUR, 'majeur'), (KS_MINEUR, 'mineur')):
            c = np.corrcoef(np.roll(chroma, -r), profil)[0, 1]
            scores.append((c, NOTES[r], mode))
    scores.sort(reverse=True)

    for c, note, mode in scores[:3]:
        print(f"  {note:<5} {mode:<8} r = {c:.3f}")
    ecart = scores[0][0] - scores[1][0]
    print(f"  Écart 1er/2e : {ecart:.3f}"
          f"{'  -> ambiguïté modale' if ecart < 0.10 else ''}")

    ordre = np.argsort(chroma)[::-1][:6]
    print("  Profil chroma : " + ", ".join(f"{NOTES[j]}={chroma[j]:.2f}" for j in ordre))

    return scores[:3]


# ==============================================================================
# SECTION 3.8 — dynamique
# ==============================================================================

def analyse_dynamique(y, sr):
    """
    Section 3.8 — compression et continuité sonore.

    Le facteur de crête (crest factor) est le rapport entre valeur crête et
    valeur efficace. Un facteur faible traduit une compression marquée.

    LIMITE : ces mesures caractérisent le produit masterisé, non le jeu
    instrumental. La fiche technique du duo documente une compression insérée
    sur chaque voie de la console.
    """
    rms   = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    crete = np.max(np.abs(y))
    cf    = 20 * np.log10(crete / np.sqrt(np.mean(y ** 2)))

    db  = 20 * np.log10(rms + 1e-10)
    act = db[db > db.max() - 40]                 # exclusion des silences
    lra = np.percentile(act, 95) - np.percentile(act, 10)

    print(f"  Facteur de crête      {cf:.1f} dB")
    print(f"  Étendue dynamique     {lra:.1f} dB  (p95 - p10)")

    return dict(crest=cf, lra=lra)


# ==============================================================================
# TEMPO ET STABILITÉ
# ==============================================================================

def analyse_tempo(y, sr):
    """Estimation du tempo et de sa stabilité (écart-type des intervalles)."""
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
    tempo = float(np.atleast_1d(tempo)[0])
    d = np.diff(beats)
    stab = 100 * d.std() / d.mean()
    print(f"  Tempo (algorithme)    {tempo:.1f} BPM")
    print(f"  Stabilité du battement σ = {stab:.2f} %"
          f"{'  (instable -> risque d’erreur d’octave)' if stab > 5 else ''}")
    return tempo, stab


# ==============================================================================
# FIGURES (optionnel)
# ==============================================================================

def generer_figures(resultats, dossier):
    """
    Figures pour insertion dans le manuscrit.

    Écrit dans `dossier` (par défaut research/docs/figures/, référencé par
    docs/analyse_acoustique_osso.md §3.6).
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(len(resultats), 1, figsize=(10, 4 * len(resultats)))
    if len(resultats) == 1:
        axes = [axes]

    for ax, (nom, reg) in zip(axes, resultats.items()):
        t, cent = reg['temps'], reg['centroide']
        ax.plot(t, cent, lw=0.5, alpha=0.4, color='grey', label='centroïde')
        m = t < (t[-1] - FADE_EXCLU)
        ax.plot(t[m], reg['depart'] + reg['pente'] * t[m], lw=2.5, color='crimson',
                label=f"régression : {reg['pente']:+.2f} Hz/s  (R² = {reg['r2']:.3f})")
        ax.set_title(nom)
        ax.set_xlabel('temps (s)')
        ax.set_ylabel('centroïde spectral (Hz)')
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    sortie = dossier / 'osso_centroide.png'
    plt.savefig(sortie, dpi=150)
    print(f"\n  -> {sortie}")


# ==============================================================================
# PROGRAMME PRINCIPAL
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Analyse acoustique computationnelle du corpus OSSO "
                    "(cf. research/docs/analyse_acoustique_osso.md).")
    ap.add_argument('--data', default='.', metavar='DIR',
                    help="dossier contenant track1.mp3 et track2.mp3 "
                         "(défaut : répertoire courant). Ces fichiers ne sont "
                         "pas versionnés — voir l'en-tête du script.")
    ap.add_argument('--figures', nargs='?', const=str(FIGURES_DIR), default=None,
                    metavar='DIR',
                    help=f"génère les figures PNG (défaut : {FIGURES_DIR})")
    args = ap.parse_args()

    data = Path(args.data).expanduser()

    manquants = [f for f, _ in PIECES if not (data / f).exists()]
    if manquants:
        print("ERREUR — fichiers audio absents de", data.resolve(), ":",
              ', '.join(manquants))
        print("\nCes fichiers ne sont pas fournis avec le script : ce sont des")
        print("œuvres protégées, non versionnées dans le dépôt. Procure-toi les")
        print("enregistrements légalement (achat sur Bandcamp, ou autorisation")
        print("des ayants droit pour un usage de recherche), puis place-les dans")
        print("ce dossier ou indique-le avec --data.")
        return 1

    regressions = {}

    for i, (fichier, nom) in enumerate(PIECES, 1):
        separateur(f"PIÈCE {i} — {nom}")
        prefixe = data / f'p{i}'

        mid, side, sr = preparer(data / fichier, prefixe)
        print(f"  Durée : {len(mid)/sr:.1f} s   ({sr} Hz)")

        separateur("3.1  Organisation stéréophonique", 2)
        analyse_mid_side(mid, side, sr)

        separateur("3.2  Nature du timbre", 2)
        analyse_timbre(mid, sr)

        separateur("3.3  Pics de résonance (Praat)", 2)
        analyse_resonances(f'{prefixe}_mid.wav')

        separateur("Tempo et stabilité", 2)
        tempo, stab = analyse_tempo(mid, sr)

        separateur("3.4  Spectre de modulation", 2)
        y22 = librosa.load(f'{prefixe}_mid.wav', sr=22050, mono=True)[0]
        mods = spectre_modulation(y22, 22050)

        separateur("3.5  Validation du niveau métrique", 2)
        pics = sorted({p for v in mods.values() for p in v})
        candidats = sorted({round(tempo, 1), round(tempo / 2, 1),
                            round(tempo * 2, 1), round(tempo * 3 / 4, 1)})
        correction_metrique(pics, candidats)

        separateur("3.6  Régression du centroïde spectral", 2)
        regressions[nom] = regression_centroide(mid, sr)

        separateur("3.7  Estimation de tonalité", 2)
        estimation_tonalite(y22, 22050)

        separateur("3.8  Dynamique", 2)
        analyse_dynamique(mid, sr)

    if args.figures:
        separateur("GÉNÉRATION DES FIGURES")
        generer_figures(regressions, args.figures)

    separateur("ANALYSE TERMINÉE")
    return 0


if __name__ == '__main__':
    sys.exit(main())
