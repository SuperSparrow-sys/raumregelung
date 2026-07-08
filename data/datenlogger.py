import os
import sqlite3
from datetime import datetime

DB_PFAD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gesamtdaten.db")

def _init_db():
    with sqlite3.connect(DB_PFAD) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messdaten (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zeitstempel TEXT,
                temp_sensor_1 REAL,
                temp_sensor_2 REAL,
                temp_sensor_3 REAL,
                temp_sensor_4 REAL,
                temp_mittelwert REAL,
                sollwert REAL,
                pid_ausgabe_prozent REAL,
                ventil_position_prozent REAL,
                status TEXT,
                hand_modus INTEGER DEFAULT 0
            )
        """)
        # Migration: Spalte nachträglich hinzufügen falls DB älter ist
        try:
            conn.execute("ALTER TABLE messdaten ADD COLUMN hand_modus INTEGER DEFAULT 0")
        except Exception:
            pass  # Spalte existiert bereits
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messdaten_zeit ON messdaten(zeitstempel)")
        existiert = conn.execute("SELECT COUNT(*) FROM messdaten").fetchone()[0]
        if existiert == 0:
            conn.execute("INSERT INTO messdaten (zeitstempel, status) VALUES (?, 'INIT')",
                         [datetime.now().isoformat(timespec="seconds")])

class DatenLogger:
    def __init__(self):
        _init_db()
        self._conn = sqlite3.connect(DB_PFAD, check_same_thread=False)

    def schreibe_zeile(self, temps, mittelwert, sollwert, ausgabe, ventil_position, status="OK", hand_modus=False):
        sql = "INSERT INTO messdaten (zeitstempel, temp_sensor_1, temp_sensor_2, temp_sensor_3, temp_sensor_4, temp_mittelwert, sollwert, pid_ausgabe_prozent, ventil_position_prozent, status, hand_modus) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        values = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        values += [t if t == t else None for t in temps]
        values += [mittelwert, sollwert, ausgabe]
        values += [ventil_position if ventil_position == ventil_position else None, status, 1 if hand_modus else 0]
        self._conn.execute(sql, values)
        self._conn.commit()

    def schliessen(self):
        try:
            self._conn.close()
        except Exception:
            pass
