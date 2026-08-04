# Configuration du banc d'ACCORDAGE — ESP32-S3 (MicroPython).
#
# Ce banc : soufflet motorisé (axe pas-à-pas + table X) pour l'air, matrice
# d'électro-aimants (24 MG + 47 MD) pour presser les boutons, capteurs P/T +
# débit, OLED. L'excitation électromagnétique et sa mesure fine sont faites
# côté PC (interface Behringer + OUTTA) sur le banc de RECHERCHE — pas ici.
#
# ⚠ GPIO par défaut à VÉRIFIER contre ton câblage. Bring-up actionneurs
# débranchés.

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

# --- Axes pas-à-pas STEP/DIR (A4988/DRV8825, /EN commun actif bas) -----------
PIN_DRV_ENABLE = 3
# Soufflet motorisé (remplace la turbine) : table X qui comprime le soufflet.
AX_BELLOWS = dict(step=4, dir=5, sw=13, inv=False, spr=1600, mm_per_rev=8.0)
BELLOWS_TRAVEL_MM = 120.0    # course utile de la table (à mesurer)
# Section (vis) et clapet — bancs à géométrie modulaire.
AX_SCREW = dict(step=6,  dir=7,  sw=14, inv=False, spr=1600, mm_per_rev=8.0)
AX_CLAP  = dict(step=15, dir=16, sw=21, inv=False, spr=1600, mm_per_rev=None)
SECTION_WIDTH_MM = 15.0

# --- Électrovanne + bridage --------------------------------------------------
PIN_VANNE = 12
PIN_CLAMP = 40

# --- Matrice d'électro-aimants (boutons) : chaîne de 74HC595 → TPL7407 ------
PIN_SR_DATA = 35            # SER
PIN_SR_CLOCK = 36           # SRCLK
PIN_SR_LATCH = 37           # RCLK
PIN_SR_OE = 38             # /OE (PWM pour le maintien basse puissance ; None si câblé à GND)
BTN_LH = 24                # boutons main gauche
BTN_RH = 47                # touches main droite
HOLD_DUTY = 400            # maintien 0..1000 (40 %) via PWM sur /OE
HOLD_PWM_FREQ = 1000

# --- Boucle, acquisition & télémétrie ----------------------------------------
SAMPLE_HZ = 50
TELEM_HZ = 20
DISPLAY_HZ = 5
ACQ_HZ = 150
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

FW_ID = "banc-accordage"
FW_VERSION = "0.3.0"
