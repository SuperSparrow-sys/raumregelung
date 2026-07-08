from __future__ import annotations

import json
import logging
import os
import socket
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

BASE = Path(__file__).parent
FRONTEND_DIR = BASE / "frontend"
DB_PFAD = str(BASE / "gesamtdaten.db")

app = Flask(__name__, static_folder=str(FRONTEND_DIR / "static"), static_url_path="/static")
log = logging.getLogger("web")

# Live-Daten: werden von main.py jeden Regelzyklus aktualisiert
_live: dict = {}


def _init_logging():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


_init_logging()


def setze_live_daten(daten: dict) -> None:
    """Wird von main.py jeden Regelzyklus aufgerufen (thread-safe: dict-Zuweisung ist atomar in CPython)."""
    global _live
    _live = daten


def _db_letzte_zeile() -> dict | None:
    try:
        with sqlite3.connect(DB_PFAD) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM messdaten ORDER BY id DESC LIMIT 1").fetchone()
            return dict(row) if row else None
    except Exception:
        return None


def _db_zeitraum(kanal: str, von: str = "", bis: str = "") -> list[dict]:
    kanal_spalten = {
        "ist_temp": "temp_mittelwert",
        "sollwert": "sollwert",
        "pid_out": "pid_ausgabe_prozent",
        "ventil": "ventil_position_prozent",
        "temp_1": "temp_sensor_1",
        "temp_2": "temp_sensor_2",
        "temp_3": "temp_sensor_3",
        "temp_4": "temp_sensor_4",
    }
    spalte = kanal_spalten.get(kanal)
    if not spalte:
        return []
    try:
        with sqlite3.connect(DB_PFAD) as conn:
            sql = "SELECT zeitstempel, {} FROM messdaten WHERE {} IS NOT NULL".format(spalte, spalte)
            params = []
            if von:
                sql += " AND zeitstempel >= ?"
                params.append(von)
            if bis:
                sql += " AND zeitstempel <= ?"
                params.append(bis)
            sql += " ORDER BY id ASC"
            rows = conn.execute(sql, params).fetchall()
            return [{"t": r[0], "v": round(r[1], 4)} for r in rows if r[1] is not None]
    except Exception:
        return []


def _parse(val) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        return None if (v != v) else round(v, 4)
    except (ValueError, TypeError):
        return None


def _lade_einstellungen() -> dict:
    try:
        import runtime_settings
        return runtime_settings.laden()
    except Exception as exc:
        log.warning("Einstellungen nicht ladbar: %s", exc)
        return {"sollwert": 22.0, "Kp": 40.0, "Ki": 10.0, "Kd": 0.0, "zykluszeit_sek": 60.0}


def _alarm_anzahl() -> int:
    try:
        with sqlite3.connect(DB_PFAD) as conn:
            row = conn.execute("SELECT COUNT(*) FROM alarme WHERE bestaetigt=0").fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


KANAL_MAP = {
    "ist_temp": "Ist-Temperatur",
    "sollwert": "Sollwert",
    "pid_out": "PID-Ausgabe",
    "ventil": "Ventil-Position",
    "temp_1": "Sensor 1",
    "temp_2": "Sensor 2",
    "temp_3": "Sensor 3",
    "temp_4": "Sensor 4",
}


@app.route("/")
@app.route("/uebersicht")
def uebersicht():
    try:
        return send_from_directory(FRONTEND_DIR, "uebersicht.html")
    except Exception:
        return "<h1>frontend/uebersicht.html nicht gefunden</h1>", 500


@app.route("/diagramme")
def diagramme():
    try:
        return send_from_directory(FRONTEND_DIR, "diagramme.html")
    except Exception:
        return "<h1>frontend/diagramme.html nicht gefunden</h1>", 500


@app.route("/alarme")
def alarme():
    try:
        return send_from_directory(FRONTEND_DIR, "alarme.html")
    except Exception:
        return "<h1>frontend/alarme.html nicht gefunden</h1>", 500


@app.route("/api/daten")
def api_daten():
    # Live-Daten bevorzugen (alle 3 s aktualisiert), DB nur als Fallback
    letzte = _live if _live else (_db_letzte_zeile() or {})
    try:
        einst = _lade_einstellungen()
    except Exception:
        einst = {}
    try:
        alarm_count = _alarm_anzahl()
    except Exception:
        alarm_count = 0

    antwort = {
        "zeitstempel": letzte.get("zeitstempel", datetime.now().isoformat(timespec="seconds")),
        "sensor_1": _parse(letzte.get("temp_sensor_1")),
        "sensor_2": _parse(letzte.get("temp_sensor_2")),
        "sensor_3": _parse(letzte.get("temp_sensor_3")),
        "sensor_4": _parse(letzte.get("temp_sensor_4")),
        "mittelwert": _parse(letzte.get("temp_mittelwert")),
        "sollwert": einst.get("sollwert"),
        "pid_ausgabe": _parse(letzte.get("pid_ausgabe_prozent")),
        "ventil_position": _parse(letzte.get("ventil_position_prozent")),
        "status": letzte.get("status", ""),
        "Kp": einst.get("Kp"),
        "Ki": einst.get("Ki"),
        "Kd": einst.get("Kd"),
        "zykluszeit_sek": einst.get("zykluszeit_sek"),
        "hand_modus": letzte.get("hand_modus", einst.get("hand_modus", False)),
        "hand_stellwert": letzte.get("hand_stellwert", einst.get("hand_stellwert", 0.0)),
        "alarm_count": alarm_count,
        "db_vorhanden": letzte is not None,
    }
    return jsonify(antwort)


@app.route("/api/historie")
def api_historie():
    try:
        kanal = request.args.get("kanal", "")
        if kanal not in KANAL_MAP:
            return jsonify({"error": "Unbekannter Kanal", "kanaele": list(KANAL_MAP.keys())}), 200
        daten = _db_zeitraum(kanal, request.args.get("von", ""), request.args.get("bis", ""))
        return jsonify({"kanal": kanal, "daten": daten})
    except Exception as exc:
        log.error("historie: %s", exc)
        return jsonify({"kanal": "", "daten": [], "error": str(exc)}), 200


@app.route("/api/historie/multi", methods=["POST"])
def api_historie_multi():
    try:
        body = request.get_json(silent=True) or {}
        kanaele = body.get("kanaele", [])
        von = body.get("von", "")
        bis = body.get("bis", "")
        ergebnis = {}
        for k in kanaele:
            if k in KANAL_MAP:
                ergebnis[k] = _db_zeitraum(k, von, bis)
        return jsonify({"daten": ergebnis})
    except Exception as exc:
        log.error("historie/multi: %s", exc)
        return jsonify({"daten": {}}), 200


@app.route("/api/einstellungen", methods=["GET", "POST"])
def api_einstellungen():
    try:
        import runtime_settings
        if request.method == "POST":
            updates = request.get_json(silent=True) or {}
            if updates:
                ok, err, neu = runtime_settings.validiere_und_speichere(updates)
                if not ok:
                    return jsonify({"success": False, "error": err}), 200
                log.info("Einstellungen geändert: %s", updates)
                return jsonify({"success": True, "einstellungen": neu})
            return jsonify({"success": False, "error": "Leerer Request-Body"}), 200
        return jsonify({"success": True, "einstellungen": runtime_settings.laden()})
    except Exception as exc:
        log.error("einstellungen: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 200


@app.route("/api/kanaele")
def api_kanaele():
    return jsonify(KANAL_MAP)


@app.route("/api/alarme", methods=["GET"])
def api_alarme_get():
    try:
        nur_aktive = request.args.get("aktiv", "0") == "1"
        from control.alarmmanager import AlarmManager
        am = AlarmManager()
        alarms = am.hole_alarme(nur_aktive=nur_aktive)
        return jsonify({"alarme": alarms, "anzahl_aktiv": am.aktive_anzahl()})
    except Exception as exc:
        log.error("alarme get: %s", exc)
        return jsonify({"alarme": [], "anzahl_aktiv": 0, "error": str(exc)}), 200


@app.route("/api/alarme/quittieren", methods=["POST"])
def api_alarme_quittieren():
    try:
        body = request.get_json(silent=True) or {}
        alarm_id = body.get("id")
        if alarm_id is None:
            return jsonify({"success": False, "error": "Keine ID angegeben"}), 200
        from control.alarmmanager import AlarmManager
        am = AlarmManager()
        am.bestaetige(int(alarm_id))
        return jsonify({"success": True, "anzahl_aktiv": am.aktive_anzahl()})
    except Exception as exc:
        log.error("alarme quittieren: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 200


@app.route("/api/status")
def api_status():
    db_da = os.path.exists(DB_PFAD)
    zeilen = 0
    if db_da:
        try:
            with sqlite3.connect(DB_PFAD) as conn:
                zeilen = conn.execute("SELECT COUNT(*) FROM messdaten").fetchone()[0]
        except Exception:
            pass
    return jsonify({
        "db_vorhanden": db_da,
        "db_zeilen": max(0, zeilen),
        "db_pfad": DB_PFAD,
        "server_zeit": datetime.now().isoformat(timespec="seconds"),
        "python_version": sys.version.split()[0],
    })


if __name__ == "__main__":
    port = 5050
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "localhost"
    print("=" * 50)
    print("  Eisenwerk – Visualisierung")
    print(f"  Übersicht:  http://localhost:{port}")
    print(f"  Diagramme:  http://localhost:{port}/diagramme")
    print(f"  Alarme:     http://localhost:{port}/alarme")
    print(f"  API-Daten:  http://localhost:{port}/api/daten")
    print(f"  Status:     http://localhost:{port}/api/status")
    print("=" * 50)
    try:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    except Exception as exc:
        print(f"FEHLER: Server konnte nicht starten: {exc}", file=sys.stderr)
        sys.exit(1)
