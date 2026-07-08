"""
Konfiguration der Kälte-Regelung.
Diese Werte an die eigene Anlage anpassen.
"""

# ---- Serielle Schnittstelle für den RS-485 Modbus-RTU Bus ----
# WICHTIG: Den richtigen COM-Port eintragen!
# Windows: Geräte-Manager -> Anschlüsse (COM & LPT) -> USB Serial Port
#          Typisch: "COM3", "COM4", ...
# Linux:   "/dev/ttyUSB0" oder "/dev/ttyACM0"
SERIELLER_PORT = "/dev/ttySC1"   # Linux: z.B. "/dev/ttySC1" | Windows: z.B. "COM3"

# ---- Modbus-Kommunikationsparameter ----
# Müssen bei ALLEN Geräten am Bus identisch eingestellt sein
# (bei den Sensoren per DIP-Schalter, beim Ventil per ZTH EU / PC-Tool).
BAUDRATE = 38400
PARITAET = "E"      # "N", "E" oder "O"  – Belimo-Standard: Even (8E1)
STOPBITS = 1         # 1 bei Paritaet "E" (Belimo-Standard)

# ---- Modbus-Slave-Adressen der 4 Temperaturfühler (22DT-15..) ----
TEMPERATUR_SENSOR_ADRESSEN = [1, 2, 3, 4]

# ---- Modbus-Slave-Adresse des Kälte-Ventilantriebs (SR24A-MOD) ----
VENTIL_ADRESSE = 5

# ---- Sollwert Raumtemperatur [°C] ----
SOLLWERT_TEMPERATUR = 22.0

# ---- PID-Parameter (Kp dimensionslos, Ki/Kd in Sekunden) ----
PID_KP = 40.0
PID_KI = 600.0   # 10 Minuten
PID_KD = 0.0

# ---- Regelzyklus / Speicherintervall [Sekunden] ----
ZYKLUSZEIT_SEK = 3.0          # PID-Berechnung und Ventilschreiben (20x pro Minute)
DB_LOG_INTERVALL_SEK = 60.0   # Speicherung in die Datenbank

# ---- CSV-Logdatei ----
LOG_DATEI = "regelung_log.csv"
