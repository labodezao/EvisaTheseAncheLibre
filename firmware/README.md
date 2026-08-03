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

## Câblage (défauts `config.py`, à vérifier)

- **I2C** (OLED + BMP280 + SFM3000) : SDA=GPIO8, SCL=GPIO9, 400 kHz.
- **Stepper** : GPIO4/5/6/7 ; fin de course SW1=GPIO13, inversion SW2=GPIO14.
- **Vanne** GPIO10 · **Turbine (PWM)** GPIO11 · **Bridage** GPIO12.
- **Excitation EM** : PWM GPIO15, enable GPIO16.
- **UART** (bring-up) : TX=GPIO17, RX=GPIO18, 115200 bauds.

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
| `PING` | → `PONG` |
| `ID` | → identifiant + version |
| `TARE` | capture la pression ambiante (référence) |
| `HOME` | référence le moteur sur le fin de course |
| `VALVE 0\|1` | ferme / ouvre la vanne |
| `CLAMP 0\|1` | bridage de l'anche |
| `BLOW n` | turbine en boucle ouverte (0..1000) |
| `PRESSURE p` | consigne de pression relative (Pa) — régulation turbine |
| `STEP n` | déplace le moteur de n pas (signe = sens) |
| `INVERT` | inverse le sens du soufflet |
| `EM f a` | excitation EM à f Hz, amplitude a (0..1000) |
| `SWEEP f0 f1 dur [a]` | balayage EM de f0 à f1 en `dur` s |
| `STREAM 0\|1 [hz]` | active/désactive la télémétrie (+ cadence) |
| `STOP` | met tous les actionneurs en sécurité |

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
