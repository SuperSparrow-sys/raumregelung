"""
Konfiguration der Kälte-Regelung.
Diese Werte an die eigene Anlage anpassen.
"""

# ---- Serielle Schnittstelle für den RS-485 Modbus-RTU Bus ----
# WICHTIG: Auf Windows "COM3" (oder passenden COM-Port) eintragen!
#          Auf Linux   "/dev/ttyUSB0" (oder passendes ttyUSB-Gerät)
SERIELLER_PORT = "/dev/ttySC0"

# ---- Modbus-Kommunikationsparameter ----
# Müssen bei ALLEN Geräten am Bus identisch eingestellt sein
# (bei den Sensoren per DIP-Schalter, beim Ventil per ZTH EU / PC-Tool).
BAUDRATE = 38400
PARITAET = "N"      # "N", "E" oder "O"
STOPBITS = 2         # 2 bei Paritaet "N" (Werkseinstellung), sonst 1

# ---- Modbus-Slave-Adressen der 4 Temperaturfühler (22DT-15..) ----
TEMPERATUR_SENSOR_ADRESSEN = [1, 2, 3, 4]

# ---- Modbus-Slave-Adresse des Kälte-Ventilantriebs (SR24A-MOD) ----
VENTIL_ADRESSE = 10

# ---- Sollwert Raumtemperatur [°C] ----
SOLLWERT_TEMPERATUR = 22.0

# ---- PID-Parameter (Kp dimensionslos, Ki/Kd in Minuten) ----
PID_KP = 40.0
PID_KI = 10.0
PID_KD = 0.0

# ---- Regelzyklus / Speicherintervall [Sekunden] ----
ZYKLUSZEIT_SEK = 60.0

# ---- CSV-Logdatei ----
LOG_DATEI = "regelung_log.csv"
