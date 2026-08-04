# Banc d'accordage — firmware ESP32-S3 (MicroPython)

Contrôle de la partie **jeu/mesure physique** du banc d'accordage (soufflet
motorisé, électro-aimants sur les boutons, vanne, capteurs pression/débit/
température, OLED) et **télémétrie** vers l'accordeur web. Réécriture propre et
stable de l'ancien script Pyboard : bugs corrigés (conflit de broche, `__init__`
qui ne rendait pas la main, gestionnaire d'exceptions non installé, boucle
bloquée, aucun filtrage), architecture modulaire et **agnostique au transport**.

> ⚠ Firmware **non testé sur matériel** : vérifie la table de broches
> (`config.py`) et les échelles capteurs avant le premier essai sous tension.
> Fais un premier bring-up **actionneurs débranchés**.

## Architecture

```
main.py            boot : watchdog, gestionnaire d'exceptions, transports
bench.py           contrôleur async (échantillonnage, régulation, séquences)
config.py          table de broches + constantes (À ADAPTER)
filters.py         médiane + passe-bas (stabilise pression/débit)
display.py         OLED SSD1306 (P / Q / T / état)
drivers/
  bmp280.py        pression + température (I2C)
  sfm3000.py       débit massique (I2C)
  actuators.py     axes pas-à-pas (soufflet, section, clapet) + sorties TOR
  shiftreg.py      matrice d'électro-aimants (74HC595 → TPL7407, boutons)
transport_uart.py  lien série (bring-up / pont USB-UART)
transport_ws.py    WiFi + WebSocket (lien principal vers l'accordeur)
```

Tout passe par un **seul contrôleur** (`Bench`) : les transports ne font
qu'acheminer des **commandes texte** et diffuser la **télémétrie JSON**.

> **Module ACCORDAGE.** Ce firmware pilote le banc d'accordage : soufflet
> motorisé + électro-aimants sur les boutons pour jouer les notes, capteurs,
> OLED. L'**excitation électromagnétique** et sa **mesure fine** sont sur le
> **banc de recherche** (`../research/`, PC + interface Behringer), pas ici.

## Rig couvert

- **Soufflet motorisé** (axe pas-à-pas + table X) : source d'air, en
  **vitesse** (`BELLOWS`) ou en **pression asservie** (`PRESSURE`) ; auto-
  inversion aux bornes de course (pousser/tirer).
- **Matrice d'électro-aimants** (74HC595 → TPL7407) : **24 boutons MG + 47 MD**,
  `PRESS canal 0|1`, maintien basse conso par PWM sur `/OE`.
- **Axes** section-vis (`SECTION`, surface = x·15 mm) et clapet (`CLAP`, °).
- **Électrovanne**, **bridage**, capteurs **BMP280** (P/T) + **SFM3000** (débit).
- **Acquisition rapide** P/Q/T (≤150 Hz) streamée pour synchro audio.

## Câblage (défauts `config.py`, à vérifier)

- **I2C** (OLED + BMP280 + SFM3000) : SDA=GPIO8, SCL=GPIO9.
- **Axes** : soufflet 4/5 (SW13), section 6/7 (SW14), clapet 15/16 (SW21) ; `/EN`=GPIO3.
- **74HC595** (boutons) : DATA=35, CLOCK=36, LATCH=37, /OE=38 (PWM maintien).
- **Vanne** GPIO12 · **Bridage** GPIO40.
- **UART** (bring-up) : TX=GPIO43, RX=GPIO44.

## Installation

```bash
# MicroPython ESP32-S3 récent (asyncio intégré). Puis :
mpremote connect <port> mip install ssd1306
mpremote connect <port> mip install microdot microdot.websocket   # si WiFi
mpremote connect <port> fs cp -r firmware/. :        # copie le firmware
mpremote connect <port> reset
```

Pour le WiFi, renseigne `WIFI_SSID` / `WIFI_PASS` dans `config.py`
(vide = UART seul).

## Protocole (lignes texte)

**Commandes** (une par ligne) :

| Commande | Effet |
|---|---|
| `PING` / `ID` | → `PONG` / identifiant+version |
| `HOME` | référence les 3 axes (soufflet, section, clapet) sur fins de course |
| `TARE` | capture la pression ambiante (référence) |
| `BELLOWS n` | vitesse directe du soufflet `n` pas/s (0 = arrêt), coupe l'asserv |
| `PRESSURE p` | consigne de pression `p` Pa → asservit la vitesse du soufflet |
| `SECTION mm` | amène la vis de section à `mm` (surface = mm·15) |
| `CLAP deg` | amène le clapet à l'angle `deg` |
| `PRESS canal 0\|1` | électro-aimant du bouton `canal` (0..70) relâché/pressé |
| `ALLOFF` | relâche tous les électro-aimants |
| `VALVE 0\|1` / `VALVE PULSE ms` | électrovanne (état ou impulsion) |
| `CLAMP 0\|1` | bridage de l'anche |
| `ACQUIRE dur [hz]` | rafale P/Q/T horodatée streamée (`A t p q temp`) |
| `STREAM 0\|1 [hz]` | télémétrie live (JSON) on/off + cadence |
| `STOP` | met tous les actionneurs en sécurité (soufflet, vanne, aimants) |

**Plan d'expériences** (l'ancien `Mesures.py` PC+rshell) se rejoue ainsi depuis
l'accordeur : pour chaque point `SECTION`→`PRESSURE`/`BELLOWS`→`CLAP`→
`PRESS canal 1`→`ACQUIRE`, pendant que le navigateur enregistre l'audio et
l'analyse (pitch, attaque `Tresp`, formants/résonances via Matrix Pencil,
impédance P/Q). L'orchestration DOE automatique (grille Section×Pression×Clapet)
est pilotée par l'onglet **« Banc »** de l'accordeur.

**Télémétrie** (JSON, une trame par ligne, ~20 Hz) :

```json
{"t":123456,"p":842.1,"q":3.204,"T":21.7,"bellv":300,"sp":null,
 "xmm":12.0,"surf":180.0,"clap":8.0,"valve":1,"clampd":0,"btn":2,"st":"pret"}
```

`t` ms, `p` Pa relatifs (après tare), `q` slm, `T` °C, `bellv` vitesse soufflet
(pas/s), `sp` consigne de pression, `xmm`/`surf` position/surface de section,
`clap` angle clapet, `btn` nombre d'aimants actifs, `st` état. Horodatage `t` =
pont pour **synchroniser** avec les mesures acoustiques de l'accordeur (f(p),
diagramme de phase, résonance).

## Lien avec l'accordeur web

Côté navigateur, l'onglet **« Banc »** se connecte :
- **sans fil** au WebSocket `ws://<ip-esp32>:8266/ws` (objectif principal), ou
- **filaire** via l'API Web Serial (pont USB-UART sur les broches UART).

Il enregistre la télémétrie **horodatée** en parallèle de l'analyse acoustique
(zoom, Matrix Pencil), pour tracer f(p), les caractéristiques pression-hauteur,
et rejouer un plan d'expériences (DOE) automatique en corrélant chaque point
pneumatique avec la réponse acoustique mesurée. L'excitation EM et sa mesure
fine (impédance, diagramme de phase, modes cavité ↔ anche) sont sur le **banc
de recherche** (`../research/`, PC + interface Behringer).

## Prochaines étapes

1. Bring-up capteurs (I2C) + OLED, actionneurs débranchés.
2. Étalonner l'échelle du SFM3000 et le zéro de pression (`TARE`).
3. Régler le gain d'asservissement `kp` (montée de pression sans oscillation).
4. Vérifier la matrice d'aimants canal par canal (`PRESS`, maintien PWM `/OE`).
5. Rejouer un DOE depuis l'onglet « Banc » + log CSV synchronisé acoustique.
