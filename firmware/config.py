# Configuration du banc d'accordage — ESP32-S3 (MicroPython).
#
# ⚠ Les numéros de GPIO ci-dessous sont des valeurs par défaut RAISONNABLES
# pour un ESP32-S3 générique : VÉRIFIE-LES contre ton câblage avant le premier
# essai. Évités : 0/45/46 (strapping), 19/20 (USB natif), 26–32 (flash/PSRAM
# sur certains modules). Un seul bus I2C partagé (OLED + BMP280 + SFM3000).

# --- Bus I2C (capteurs + écran) ---------------------------------------------
I2C_ID = 0
PIN_SDA = 8
PIN_SCL = 9
I2C_FREQ = 400_000

# Adresses I2C
ADDR_OLED = 0x3C
ADDR_BMP280 = 0x76      # 0x76 ou 0x77 selon SDO
ADDR_SFM3000 = 0x40

# --- Écran OLED SSD1306 ------------------------------------------------------
OLED_W = 128
OLED_H = 64

# --- Actionneurs pneumatiques ------------------------------------------------
PIN_VALVE = 10          # vanne (0 = fermée, 1 = ouverte) — adapte la logique
PIN_BLOW = 11           # turbine centrifuge (PWM = régime, ou tout/rien)
PIN_CLAMP = 12          # bridage de l'anche
BLOW_PWM_FREQ = 20_000  # au-dessus de l'audible

# --- Moteur pas-à-pas (position de pression / inversion de soufflet) ---------
PIN_STEP = [4, 5, 6, 7]     # 4 bobines (ordre = séquence de pas)
STEP_SW1 = 13               # fin de course (référence)
STEP_SW2 = 14               # capteur d'inversion
STEP_TRAVEL = 1600          # pas entre positions haute/basse (à mesurer)

# --- Excitation électromagnétique -------------------------------------------
PIN_EM = 15             # sortie PWM vers l'ampli de la bobine
PIN_EM_EN = 16          # enable de l'étage de puissance (0 = coupé)
EM_MIN_HZ = 20
EM_MAX_HZ = 5000

# --- Boucle & télémétrie -----------------------------------------------------
SAMPLE_HZ = 50          # cadence d'échantillonnage capteurs
TELEM_HZ = 20           # cadence de télémétrie par défaut
DISPLAY_HZ = 5          # rafraîchissement OLED
WDT_MS = 4000           # watchdog

# --- Filtrage capteurs -------------------------------------------------------
MEDIAN_N = 5            # médiane glissante (rejet des pics)
IIR_ALPHA = 0.25        # passe-bas exponentiel (0..1 ; petit = plus lisse)

# --- UART (transport filaire de bring-up / pont USB-UART) --------------------
UART_ID = 1
PIN_UART_TX = 17
PIN_UART_RX = 18
UART_BAUD = 115200

# --- WiFi (transport sans fil vers l'accordeur ; laisse SSID vide = UART seul)
WIFI_SSID = ""
WIFI_PASS = ""
WS_PORT = 8266

FW_ID = "banc-anche-libre"
FW_VERSION = "0.1.0"
