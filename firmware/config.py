# Configuration du banc d'accordage — ESP32-S3 (MicroPython).
#
# ⚠ GPIO par défaut RAISONNABLES pour un ESP32-S3 générique : VÉRIFIE-LES
# contre ton câblage. Évités : 0/45/46 (strapping), 19/20 (USB), 26–32
# (flash/PSRAM selon module). Bring-up actionneurs DÉBRANCHÉS.
#
# Rig réel (repris des Pyboards MesAnche/ValControl) : 3 axes pas-à-pas
# STEP/DIR (pression, section-vis, clapet), turbine par PWM+RC, électrovanne,
# bridage, capteurs P/T (BMP280) et débit (SFM3000), excitation EM par DDS.

# --- Bus I2C (capteurs + écran) ---------------------------------------------
I2C_ID = 0
PIN_SDA = 8
PIN_SCL = 9
I2C_FREQ = 400_000
ADDR_OLED = 0x3C
ADDR_BMP280 = 0x76
ADDR_SFM3000 = 0x40
OLED_W = 128
OLED_H = 64

# --- Axes pas-à-pas STEP/DIR (drivers type A4988/DRV8825) --------------------
# Chaque axe : (step, dir, limit-switch). ENABLE/SLEEP partagé (actif bas).
PIN_DRV_ENABLE = 3          # /EN commun des drivers (0 = actif)
AX_PRESS = dict(step=4,  dir=5,  sw=13, inv=False, spr=1600)   # sens soufflet / pression
AX_SCREW = dict(step=6,  dir=7,  sw=14, inv=False, spr=1600)   # section (vis)
AX_CLAP  = dict(step=15, dir=16, sw=21, inv=False, spr=1600)   # clapet (angle)

# Géométrie (à mesurer sur ton banc)
SCREW_MM_PER_REV = 8.0      # pas de vis (mm/tour) de l'axe section
SECTION_WIDTH_MM = 15.0     # largeur du trou de section (→ surface = x·largeur)
SCREW_TRAVEL_MM = 14.0      # course utile
STEP_TRAVEL_PRESS = 1600    # pas entre positions haute/basse du soufflet

# --- Turbine (consigne de régime, 0..4095 comme l'ancien DAC) ---------------
PIN_BLOW = 11               # PWM → filtre RC → entrée consigne du variateur
BLOW_PWM_FREQ = 20_000
PIN_BLOW_EN = 10            # enable de la turbine (relais/driver)

# --- Électrovanne + bridage --------------------------------------------------
PIN_VANNE = 12              # admission d'air temporisée
PIN_CLAMP = 40             # bridage de l'anche

# --- Excitation électromagnétique (DDS AD9833 sur SPI) ----------------------
SPI_ID = 1
PIN_SPI_SCK = 36
PIN_SPI_MOSI = 35
PIN_AD9833_FSYNC = 37       # /CS du DDS
AD9833_MCLK = 25_000_000    # quartz du module (souvent 25 MHz)
PIN_EM_AMP = 17             # PWM → gain/VCA de l'ampli bobine (amplitude EM)
PIN_EM_EN = 18             # enable de l'étage de puissance EM
EM_MIN_HZ = 10
EM_MAX_HZ = 6000

# --- Boucle, acquisition & télémétrie ----------------------------------------
SAMPLE_HZ = 50             # cadence de la boucle de fond (affichage/télémétrie)
TELEM_HZ = 20
DISPLAY_HZ = 5
ACQ_HZ = 150              # cadence max de l'acquisition rapide (rafale)
WDT_MS = 4000
MEDIAN_N = 5
IIR_ALPHA = 0.25

# --- UART (bring-up / pont) --------------------------------------------------
UART_ID = 1
PIN_UART_TX = 43
PIN_UART_RX = 44
UART_BAUD = 115200

# --- WiFi (lien principal ; SSID vide = UART seul) --------------------------
WIFI_SSID = ""
WIFI_PASS = ""
WS_PORT = 8266

FW_ID = "banc-anche-libre"
FW_VERSION = "0.2.0"
