# Du sample au modèle physique — et vers un STM32 / Dream SAM5716

> Outil : onglet **« Sample → modèle »** de la GUI, modules
> [`sample_extract.py`](../banc_recherche/sample_extract.py) et
> [`synth_export.py`](../banc_recherche/synth_export.py).

## L'idée

Un sampleur rejoue un enregistrement. Un instrument à modèle physique (type
SWAM) fait tourner un **modèle** qu'on pilote en continu. Le sample ne
disparaît pas pour autant : il devient une **mesure**, celle dont on extrait
les paramètres du modèle.

C'est exactement la démarche du banc de recherche, appliquée à un fichier
plutôt qu'à une anche montée sur le soufflet : on ne cherche pas à reproduire
un son, on cherche à identifier **ce qui le produit**.

## Ce qu'on extrait, et pourquoi

| Grandeur | Ce qu'elle dit du modèle |
|---|---|
| `f0(t)`, vibrato (taux, profondeur) | Sépare la hauteur nominale du **geste**. Le modèle doit produire le vibrato, pas le rejouer figé. |
| Niveaux des partiels | La sortie du système — point de départ de la synthèse additive/modale. |
| **Inharmonicité** (cents) | La raideur du résonateur : une anche raide écarte ses partiels de l'harmonique idéale. Relie directement à `modal.py` / `reed_model.py`. |
| **Résonateur** (biquads) | Le corps de l'instrument. **Invariant avec la note** — c'est le critère qui valide l'extraction. |
| Pente de source (dB/octave de rang) | L'excitation une fois le corps retiré : anche douce = pente forte, anche mordante = pente faible. |
| Attaque **par partiel** | Les aigus s'établissent après le fondamental. C'est ce que fige un sampleur, et ce qui rend une attaque vivante. |
| Part de bruit | Souffle, frottement de roue, bruit d'écoulement. |
| Brillance ↔ niveau | La **loi de commande** du contrôleur continu : jouer fort ouvre le spectre. |

### Le point délicat : séparer la source du résonateur

Sur **une seule note tenue**, la structure harmonique (qui suit la note) et
l'enveloppe spectrale (le corps, fixe) sont superposées. Les confondre donne
un « résonateur » qui se déplace avec la hauteur jouée — donc pas un
résonateur du tout.

L'enveloppe est donc estimée en **interpolant les sommets des partiels**
(`spectral_envelope`), avec repli sur un **liftrage cepstral** quand la
hauteur n'est pas connue. Un simple lissage par moyenne glissante ne marche
pas : il faudrait une fenêtre plus large que `f0`, donc dépendante de la note.

Le test `test_resonator_invariant_across_notes` vérifie précisément ce
critère : deux notes différentes dans le même corps doivent donner la même
résonance.

**Conséquence pratique** : pour une identification sérieuse, fournis
**plusieurs notes** du même instrument (et si possible plusieurs nuances). Ce
qui est commun aux notes est le corps ; ce qui varie est la source. Une note
seule donne une estimation, pas une mesure.

## Les trois architectures possibles côté matériel

C'est la question à trancher en premier, parce qu'elle décide de tout le
reste.

Les SoC Dream de la série SAM5xxx (SAM5504, SAM5708, **SAM5716**…) sont des
moteurs **wavetable / sampleur MIDI** avec effets, pilotés par un hôte. Leur
firmware standard ne fait pas tourner un guide d'onde ni un oscillateur non
linéaire. D'où trois voies :

### 1. Le modèle tourne sur le STM32
Le Dream ne sert que de sortie audio et d'effets. C'est la voie la plus
**libre** : tout le modèle physique est à toi, en C, sur le STM32.
→ export **`.h`** (`to_c_header`) : biquads du résonateur, niveaux et
enveloppes des partiels, lois de commande. Option `fixed_point=True` pour les
coefficients en Q15.

Ordre de grandeur : un banc de 6 biquads + un oscillateur additif à 12
partiels tient très largement sur un STM32 à 100 MHz en virgule flottante.

### 2. Firmware DSP custom Dream
Si le SDK Dream (sous accord de confidentialité) expose un moteur de filtrage
programmable par voie, le modèle peut descendre dans le DSP. Mêmes
coefficients, autre format de chargement.

### 3. Approximation wavetable
La seule voie qui parle **nativement** à un moteur type Dream sans firmware
custom : on synthétise des cycles à partir des partiels mesurés, et on pilote
le morphing entre eux avec les lois extraites (brillance ↔ niveau).
→ export **`to_wavetable`** + `wavetable_to_c`.

C'est une approximation : le morphing entre cycles fixes ne reproduit pas
l'étalement de l'attaque par partiel, qui est justement ce qui fait vivre le
son. Mais c'est jouable tout de suite, sans NDA.

## Ce que cet outil ne fait pas

`synth_export.DreamAdapter` est **volontairement non implémenté**. Le
protocole de configuration d'un SAM5716 (SysEx propriétaires, format de banque
en Flash SPI, API du firmware) n'est pas public ; il vient de la documentation
constructeur. Écrire ici des adresses de registres plausibles produirait du
code qui compile, qui a l'air correct, et qui ne pilote rien.

Ce qu'il faut demander à Dream, dans l'ordre :

1. **Le 5716 expose-t-il un filtrage programmable par voie** (coefficients de
   biquads chargeables), ou seulement un sampleur + effets fixes ? → décide
   entre la voie 1/2 et la voie 3.
2. Format de chargement des banques et des wavetables.
3. Résolution et format des coefficients (flottant ? Q15 ? autre cadrage ?) —
   `to_q15()` sature volontairement plutôt que de boucler en silence, mais le
   cadrage exact dépend du DSP.

Tout ce dont l'adaptateur aura besoin est déjà calculé et accessible :
`resonator_biquads(model)`, `to_wavetable(model)`,
`model.partial_levels_db`, `model.partial_attack_s`,
`model.brightness_slope_hz_per_db`.

## Limites de mesure, à connaître

- **Résolution temporelle de l'attaque** : les attaques par partiel viennent
  d'une STFT à 4096 points ; à 22 kHz la fenêtre vaut ~186 ms, plus longue
  que bien des attaques. Les valeurs donnent l'**ordre** d'apparition des
  partiels, plus fiable que leur date absolue. L'enveloppe globale, elle,
  utilise une fenêtre courte (~23 ms).
- **Une note ne suffit pas** à séparer proprement source et résonateur (voir
  plus haut).
- **Sample monophonique obligatoire** : le suivi de hauteur par
  autocorrélation suppose une seule voix. Sur un accord, l'extraction renvoie
  `nan` plutôt que d'inventer une hauteur — c'est voulu.
- **Le sample porte sa chaîne de production** : micro, préampli, égalisation,
  compression, réverbération. Le « résonateur » extrait d'un enregistrement
  produit inclut tout cela. Pour identifier un instrument, un enregistrement
  proche et sec vaut mieux qu'un beau mixage.

## Usage

```bash
cd research
pip install -e .                     # numpy + scipy suffisent pour l'extraction
banc-recherche                       # onglet « Sample → modèle »
```

En ligne :

```python
from banc_recherche import sample_extract, synth_export
import soundfile as sf

y, sr = sf.read("anche_la3.wav")
m = sample_extract.extract(y, sr, name="anche_la3", n_partials=12)

synth_export.to_json(m, "anche_la3.json")
synth_export.to_c_header(m, "anche_la3.h", fixed_point=True)   # modèle sur STM32
synth_export.wavetable_to_c(synth_export.to_wavetable(m), "anche_la3",
                            "anche_la3_wt.h")                  # moteur wavetable
```

## Lien avec le reste de la thèse

L'extraction mesure ce que les modules du banc **prédisent** :
`modal.py` donne les fréquences propres d'une anche, `reed_model.py` son
auto-oscillation, `timbre.py` les descripteurs. Comparer l'inharmonicité
extraite d'un vrai sample aux partiels prédits par le modèle, c'est
précisément laisser la mesure contredire l'hypothèse.
