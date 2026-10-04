# Dix-sept battements de musette enregistrés (décembre 2021)

## D'où ça vient

- Les sons : `D:\GoogleDrive\Ingénierie et recherche\Ressources\python\test demodulation\`
  (`beat-01.wav` à `beat-17.wav`, 23/12/2021, 48 kHz, 4 à 8 s chacun, environ 14 Mo en tout).
  **Non copiés** : ils restent sur le Drive. Les `beat-XX.txt` du même dossier sont des
  exports texte des WAV (inutiles, voir le catalogue).
- Les scripts : `...\Thèse anche libre\modeles\anches models\anches\libre\matlab acco\hilbert processing\`
  (`f_fundamental_compose.py`, `envelope_code_python_3.py`, `hilbert process.py`...),
  et `...\Thèse anche libre\acoustique\beat frequency estimator\beats frequencies.ipynb`.

## Ce que c'est

Chaque fichier est une note de musette (deux voix légèrement désaccordées). **Précision d'Ewen (04/10/2026) : ce n'est pas un vrai accordéon. C'est une musette jouée sur un instrument samplé trouvé sur Internet.** Une
lecture rapide du spectre (`battements_lecture_rapide.csv`) donne deux raies proches et
leur écart : de 0,6 Hz (vers 164 Hz) à 5,1 Hz (vers 785 Hz), soit 4 à 13 cents. Les notes
vont d'environ Si1 à Sol4 (notation française, La3 = 440 Hz).

Précision de cette lecture : environ ± 0,2 Hz (fenêtre de 5 s, zéro-padding). Le fichier
`beat-03` est mal lu (raie d'un harmonique). C'est une première lecture, à refaire avec
`test/outils/esprit.py` ou le Matrix Pencil de l'accordeur.

## À quoi ça sert aujourd'hui

C'est un **jeu de test enregistré** pour l'accordeur web : le `CLAUDE.md` dit que le
battement (bat/min) n'est vérifié qu'en synthèse. Attention : comme le son vient d'un
instrument samplé, ce n'est pas une mesure d'anches réelles. Le battement est celui que le
sample a figé (boucle, désaccord fixé par le fabricant du sample). Il sert à tester la
lecture du battement, pas à étudier la physique des anches. Il suffit de rejouer ces WAV avec
`test/outils/rejoue.mjs` et de comparer.

## Comment relancer

`python f_fundamental_compose.py` (numpy, scipy, matplotlib) sur un WAV. Le notebook
`beats frequencies.ipynb` fait entendre un battement synthétique.
