# Banc d'accordage — firmware ESP32-S3 (MicroPython)

Contrôle de la partie **excitation/mesure physique** du banc (turbine, vanne,
moteur de pression, capteurs pression/débit/température, excitation
électromagnétique) et **télémétrie** vers l'accordeur web. Réécriture propre et
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
  actuators.py     stepper, vanne, turbine, bridage, excitation EM
transport_uart.py  lien série (bring-up / pont USB-UART)
transport_ws.py    WiFi + WebSocket (lien principal vers l'accordeur)
```

Tout passe par un **seul contrôleur** (`Bench`) : les transports ne font
qu'acheminer des **commandes texte** et diffuser la **télémétrie JSON**.

## Rig couvert (fusion des deux Pyboards MesAnche + ValControl)

- **3 axes STEP/DIR** (drivers A4988/DRV8825, `/EN` commun) :
  **pression** (sens soufflet), **section-vis** (`SECTION`, surface = x·15 mm),
  **clapet** (`CLAP`, angle), chacun avec fin de course (homing).
- **Turbine** : consigne 0..4095 (compat. DAC historique) en **PWM→filtre RC**
  vers ton variateur (pas de DAC nécessaire).
- **Excitation EM** : **DDS AD9833** (SPI) pour une sinus balayée propre ;
  amplitude par PWM vers le gain de l'ampli.
- **Électrovanne** temporisée, **bridage**, capteurs **BMP280** (P/T) + **SFM3000**.
- **Acquisition rapide** P/Q/T (jusqu'à 150 Hz) streamée pour synchro audio.

## Câblage (défauts `config.py`, à vérifier)

- **I2C** (OLED + BMP280 + SFM3000) : SDA=GPIO8, SCL=GPIO9.
- **Axes** : press 4/5 (SW13), screw 6/7 (SW14), clap 15/16 (SW21) ; `/EN`=GPIO3.
- **Turbine** PWM=GPIO11 (+ RC), enable=GPIO10 · **Vanne** GPIO12 · **Bridage** GPIO40.
- **EM** : SPI SCK=36 MOSI=35 FSYNC=37 ; amplitude PWM=17, enable=18.
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
| `HOME` | référence les 3 axes sur leurs fins de course |
| `TARE` | capture la pression ambiante (référence) |
| `SECTION mm` | amène la vis de section à `mm` (surface = mm·15) |
| `CLAP deg` | amène le clapet à l'angle `deg` |
| `PRESSPOS 0\|1` | sens du soufflet (inversion de pression) |
| `BLOW n` | consigne turbine 0..4095 |
| `VALVE 0\|1` / `VALVE PULSE ms` | électrovanne (état ou impulsion) |
| `CLAMP 0\|1` | bridage de l'anche |
| `EM f a` | excitation EM à f Hz, amplitude a (0..1000) |
| `SWEEP f0 f1 dur [a]` | balayage EM de f0 à f1 en `dur` s |
| `PRAMP l0 l1 dur` | rampe turbine l0→l1 en `dur` s (seuil d'auto-entretien) |
| `ACQUIRE dur [hz]` | rafale P/Q/T horodatée streamée (`A t p q temp`) |
| `STREAM 0\|1 [hz]` | télémétrie live (JSON) on/off + cadence |
| `STOP` | met tous les actionneurs en sécurité |

**Plan d'expériences** (l'ancien `Mesures.py` PC+rshell) se rejoue ainsi depuis
l'accordeur : pour chaque point `SECTION`→`BLOW`/`PRAMP`→`CLAP`→`VALVE PULSE`→
`ACQUIRE`, pendant que le navigateur enregistre l'audio et l'analyse (pitch,
attaque `Tresp`, formants/résonances via Matrix Pencil, impédance P/Q).

**Télémétrie** (JSON, une trame par ligne, ~20 Hz) :

```json
{"t":123456,"p":842.1,"q":3.204,"T":21.7,"emHz":0,"emA":0,
 "blow":300,"valve":1,"clamp":0,"pos":1,"st":"pret","sp":null}
```

`t` ms, `p` Pa relatifs (après tare), `q` slm, `T` °C, `emHz/emA` excitation,
`st` état. Horodatage `t` = pont pour **synchroniser** avec les mesures
acoustiques de l'accordeur (f(p), diagramme de phase, résonance).

## Lien avec l'accordeur web

Côté navigateur, un onglet **« Banc »** (à venir) se connectera :
- **sans fil** au WebSocket `ws://<ip-esp32>:8266/ws` (objectif principal), ou
- **filaire** via l'API Web Serial (pont USB-UART sur les broches UART).

Il enregistrera la télémétrie **horodatée** en parallèle de l'analyse
acoustique (zoom, Matrix Pencil), pour tracer f(p), les caractéristiques
pression-hauteur, et corréler un balayage EM avec la réponse mesurée
(résonance, couplage modes cavité ↔ anche).

## Prochaines étapes

1. Bring-up capteurs (I2C) + OLED, actionneurs débranchés.
2. Étalonner l'échelle du SFM3000 et le zéro de pression (`TARE`).
3. Régler le gain de régulation `kp` (montée de pression sans oscillation).
4. Sécuriser l'étage EM (courant bobine) avant excitation.
5. Onglet « Banc » dans l'accordeur (WebSocket) + log CSV synchronisé.
