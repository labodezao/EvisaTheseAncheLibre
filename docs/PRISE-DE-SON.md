# Prise de son : garantir qu'elle est fiable, et le dire (v61, 14/10/2026)

Ewen : « un accordeur professionnel doit garantir que la prise de son est fiable, et le dire ».
Origine : deux sessions du 14/10/2026 (07:28 et 07:53) mesurées avec un micro USB générique
(« Microphone (USB Audio Devive) 0020:0b21 ») au lieu du Zoom H6, avec l'effet vocal de Windows
(suppression de bruit) actif. Diagnostic complet : `J:\claude\tmp\accordeur_session_2026-10-14\diagnostic.md`.
Ce qu'il montrait dans le signal PC et pas dans celui du H6 : 1629 plages de zéros exacts de 1 ms et plus en
2 min (jusqu'à 23 ms), des pauses à -88 dBFS là où le H6 enregistre le bruit du soufflet (-70 à -84),
des amplitudes relatives de partiels instables (écart type 2,5 dB contre 1 à 1,8 dB entre deux capsules XY),
un ronflement de 50 Hz à +28 dB.

## Ce qui s'affiche

- **La barre du micro**, en haut de tous les écrans (et en haut d'`ancien.html`) : « Micro : <nom> · <fréquence réelle> Hz ·
  <n> canaux ». La fréquence et les canaux sont ceux que le flux livre vraiment (`AudioData`), pas ceux demandés.
  Un appui ouvre la liste des micros branchés (`enumerateDevices`), le meilleur est marqué « conseillé ».
- **Le choix est mémorisé par `deviceId`** (`reglages.deviceId` ; `cfg.deviceId` dans l'ancienne page). Débranché, le
  micro par défaut sert et la barre le dit ; rebranché pendant la session, il est repris. Un micro qui disparaît en
  cours de route (piste `ended`) relance sur le micro par défaut avec un avis.
- **La proposition** : si plusieurs micros sont branchés et que celui qui sert vaut nettement moins que le meilleur,
  la barre le dit avec un bouton « utiliser ». Notes (`prise-micro.js`, `scoreMicro`) : interface audio reconnue (Zoom,
  Focusrite, Scarlett, Behringer X-Air, Steinberg, PreSonus, Rode, Shure…) +100 ; générique (« USB Audio Device »,
  Realtek, réseau de microphones) -15 ; virtuel (VB-Cable, Voicemeeter, DroidCam…) -50 ; entrée « Communications » de
  Windows -70 ; casque Bluetooth / « Hands-Free » -90 ; alias « Par défaut » -10. Proposition à partir de 30 points
  d'écart, jamais pour le même appareil sous deux noms (`groupId`).
- **Le bandeau de la prise** : une consigne par défaut détecté, la plus grave en tête, avec le geste exact (Windows :
  « Paramètres > Système > Son > Entrée > <nom du micro> > Améliorations audio : Désactivées » ; macOS, téléphone et
  autres : leurs gestes). « Compris » le masque jusqu'à ce que le défaut disparaisse puis revienne.
- **Prise douteuse** : tant qu'un défaut est actif, chaque image du moteur porte `prise.douteuse`. La mesure
  (`lireTick`) n'est alors jamais « juste » ni « loin » (`etat` nul, pas de forme d'état, strobe et pastilles neutres,
  contour en tirets), jamais validée automatiquement, jamais comptée dans la série de validation ; le message d'Accorder
  dit « prise douteuse : suppresseur de bruit » ; le chiffre reste lisible (on ne cache rien). Les mesures du carnet
  gardent `douteuse: true`. Dans l'ancienne page : verdict « prise douteuse » en tirets.

## Ce que le Worker contrôle (`dsp/prise.js`)

Les seuils sont dans `SEUILS` ; ils ont été fixés sur des sons de synthèse (`test/synthese-prise.mjs` : un accordéon qui
joue et se tait, avec les défauts ajoutés un à un), pas sur les sessions d'Ewen.

| Code | Signature | Seuil |
|---|---|---|
| `gate` | plages de zéros exacts de 1 à 250 ms (au-delà : micro coupé, pas une porte), comptées dans les blocs de 100 ms dont les zéros ne dépassent pas 60 % (sinon : plancher sous la quantification d'un micro très calme) ; ou plancher de pause coupé net (de -80/-58 dBFS depuis 3 blocs à -84 ou moins, perte d'au moins 9 dB en 100 ms, plat ensuite) | 5 plages en 30 s ; 4 coupures en 60 s |
| `pompage` | traitement dynamique : la raie du secteur, d'amplitude vraie constante, suit le niveau de la fenêtre | écart type 2 dB et corrélation au niveau ≤ -0,6 sur 8 fenêtres de ronflement au moins |
| `trous` | date du flux (`AudioData.timestamp`) face au compte d'échantillons, la dérive lente de l'horloge suivie | écart de plus de 5 ms (dans les deux sens : perte ou doublon) |
| `ecretage` | 3 échantillons d'affilée à plus de 0,985 | 5 événements en 10 s |
| `secteur` | raie à 50 (ou 60) Hz de 15 dB au-dessus des voisines (±4 et ±6 Hz, fenêtre de Hann de 2 s) et une harmonique 2 ou 3 de 8 dB, crête au-dessus de -85 dBFS | 70 % de 6 fenêtres au moins |
| `lent` | fréquence d'échantillonnage du flux de 16 kHz ou moins | immédiat |
| `bluetooth` | le nom du micro (« Hands-Free », AirPods, Jabra…) : le signal ne le dit pas, la page le déclare au Worker | immédiat |

Limites assumées :

- Le **pompage** n'est vu que si le ronflement du secteur est là : il sert de référence d'amplitude constante. Sans lui,
  rien dans le signal ne permet de séparer un compresseur du soufflet qui varie tout seul (le fond de pause des prises du
  H6 monte de 12 à 23 dB d'une pause à l'autre ; une première version qui comptait ces remontées donnait 3 à 4 fausses
  alertes par minute sur le H6, elle a été retirée). Le contrôle ne dit alors rien du pompage : il ne dit pas « pas de
  pompage ».
- Une alerte n'est datée qu'une fois assez de preuves reçues (la première plage de zéros est vue à 1,3 s, le
  ronflement après 12 s) ; le début de l'épisode est ramené à la première preuve (`depuis_s`), mais la mention
  « prise douteuse » de l'écran et la colonne `prise` du CSV ne portent que sur les images postérieures à la décision.
  Le JSON de la session donne les épisodes avec leur vrai début pour corriger après coup.
- Les 1,0 s de démarrage du flux ne sont pas jugées.
- Des zéros voulus (annonce vocale, son de référence : `couperMesure`) suspendent le contrôle (`priseMuet`).

## Ce que la session écrit

- `debut` du JSON : le début de la capture (le Worker date la session quand il commence à la graver), plus l'arrivée du
  premier morceau, 10 s plus tard (écart de 10 s relevé dans les deux sessions du 14/10). Le nom de la session suit.
- `micro_detail` : `label`, `device_id_hash` et `group_id_hash` (SHA-256 tronqué à 12 caractères : on reconnaît le même
  micro d'une session à l'autre sans écrire l'identifiant), `get_settings` complet (hors identifiants),
  `get_capabilities`, `contraintes_demandees`, `classement` (interface, générique, Bluetooth, communications, virtuel), `note`.
- `prise` : `saine`, `episodes` (code, `debut_s`, `fin_s`, `n`, détail ; secondes de la session), `trous` (`t_s`, `ms`),
  `resume` (plages de zéros, plus longue plage, dérive de l'horloge du micro en ppm), `canaux_flux`.
- CSV : colonne `prise` en dernier (codes en cours séparés par `+`, vide si la prise est saine).

## Validation sur les prises réelles du 14/10/2026

`node test/outils/prise_sessions.mjs --alerte <wav PC...> --propre <wav H6...>` (blocs de 512 comme le Worker) :

| Prise | Durée | Alertes (première) | Plages de zéros |
|---|---|---|---|
| PC essai 1 (micro USB, 48 kHz) | 208,5 s | `gate` à 1,3 s, `secteur` à 34 s | 570 |
| PC essai 2 (micro USB, 48 kHz) | 121,9 s | `gate` à 1,3 s, `secteur` à 52 s | 1584 |
| H6 essai 1, canal gauche et droit (44,1 kHz, 24 bits) | 210,4 s | aucune | 0 |
| H6 essai 2, canal gauche et droit (44,1 kHz, 24 bits) | 81,9 s | aucune | 0 |

Les deux prises PC déclenchent « suppresseur de bruit » ; les quatre pistes du H6 n'ont aucune fausse alerte. (Le WAV du
H6 de l'essai 1 n'est plus dans `J:\down` : ses deux canaux viennent des tableaux extraits par les scripts du
diagnostic.) Le pompage et les blocs perdus ne sont pas déclenchés sur ces prises, ce que le diagnostic confirme (pas de
trou de bloc repérable dans le WAV PC ; le saut de 45 ms de l'essai 1 n'était pas dans les échantillons).

## Tests

- `test/prise.test.mjs` : prise propre (90 s, 44,1 kHz, plancher à -82 et -100 dBFS, notes graves à 49 et 100 Hz) sans
  aucune alerte ; porte à zéros, plancher coupé, ronflement 50/60 Hz, gain automatique, écrêtage, blocs perdus ou
  doublés avec dérive de 125 ppm et gigue de 0,3 ms, 8 et 16 kHz, micro coupé, fin d'alerte.
- `test/prise-micro.test.mjs` : reconnaissance et note des micros, proposition, micro débranché, consignes (geste exact),
  JSON (début, micro, prise, aucun identifiant en clair), mesure douteuse de l'interface (jamais « juste », jamais
  validée), et le Worker de bout en bout sur un flux d'`AudioData` simulé.

## Ce qui reste

- Une prise propre au Zoom H6 choisi dans l'accordeur, effets Windows coupés, à refaire par Ewen (critère du diagnostic :
  rapport PC/H6 des partiels à 1 dB environ, plancher comparable, plus de zones mortes dans les pauses) : le contrôle
  doit rester muet.
- Les gestes pour Linux et pour les pilotes qui n'ont pas de « Améliorations audio » (ASIO4ALL, interfaces à pilote
  propre) sont génériques.
