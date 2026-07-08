import os
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("alarm")

DB_PFAD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gesamtdaten.db")

def _init_db():
    with sqlite3.connect(DB_PFAD) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alarme (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zeitstempel TEXT,
                typ TEXT,
                text TEXT,
                sensor TEXT,
                wert REAL,
                grenze REAL,
                bestaetigt INTEGER DEFAULT 0,
                bestaetigt_um TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarme_bestaetigt ON alarme(bestaetigt)")

class AlarmManager:
    def __init__(self):
        _init_db()
        self._zustand = {}

    def verbindungs_abbruch(self, sensor_name):
        if self._zustand.get(sensor_name) == "abbruch":
            return
        self._hinzufuegen(sensor_name, None, None,
            f"{sensor_name} nicht erreichbar", "Warnung")
        self._zustand[sensor_name] = "abbruch"

    def verbindung_wiederhergestellt(self, sensor_name):
        if sensor_name in self._zustand:
            del self._zustand[sensor_name]
            # Offene Alarme für dieses Gerät automatisch schließen
            try:
                with sqlite3.connect(DB_PFAD) as conn:
                    conn.execute(
                        "UPDATE alarme SET bestaetigt=1, bestaetigt_um=? "
                        "WHERE sensor=? AND bestaetigt=0",
                        (datetime.now().isoformat(timespec="seconds"), sensor_name),
                    )
            except Exception as exc:
                logger.error("Alarm auto-schließen fehlgeschlagen: %s", exc)
            logger.info("%s: wieder erreichbar – Alarm geschlossen", sensor_name)

    def systemmeldung(self, text, typ="Warnung"):
        if self._zustand.get("_system") == text:
            return
        self._hinzufuegen("System", None, None, text, typ)
        self._zustand["_system"] = text

    def system_wiederhergestellt(self):
        if "_system" in self._zustand:
            del self._zustand["_system"]

    def _hinzufuegen(self, sensor, wert, grenze, text, typ="Warnung"):
        try:
            with sqlite3.connect(DB_PFAD) as conn:
                conn.execute(
                    "INSERT INTO alarme (zeitstempel, typ, text, sensor, wert, grenze) VALUES (?, ?, ?, ?, ?, ?)",
                    (datetime.now().isoformat(timespec="seconds"), typ, text, sensor, wert, grenze))
            logger.warning("%s: %s", typ, text)
        except Exception as exc:
            logger.error("Alarm speichern fehlgeschlagen: %s", exc)

    def hole_alarme(self, nur_aktive=False, limit=200):
        try:
            with sqlite3.connect(DB_PFAD) as conn:
                conn.row_factory = sqlite3.Row
                if nur_aktive:
                    rows = conn.execute(
                        "SELECT * FROM alarme WHERE bestaetigt=0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM alarme ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def bestaetige(self, alarm_id):
        try:
            with sqlite3.connect(DB_PFAD) as conn:
                conn.execute(
                    "UPDATE alarme SET bestaetigt=1, bestaetigt_um=? WHERE id=? AND bestaetigt=0",
                    (datetime.now().isoformat(timespec="seconds"), alarm_id))
        except Exception as exc:
            logger.error("Alarm bestätigen fehlgeschlagen: %s", exc)

    def aktive_anzahl(self):
        try:
            with sqlite3.connect(DB_PFAD) as conn:
                return conn.execute("SELECT COUNT(*) FROM alarme WHERE bestaetigt=0").fetchone()[0]
        except Exception:
            return 0
