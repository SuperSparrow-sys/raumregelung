"""
Laufzeit-Einstellungen für die Kälte-Regelung.
Speichert Werte in runtime_settings.json und überschreibt config.py-Werte.
"""
import json, os, tempfile, threading

_PFAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime_settings.json")
_LOCK = threading.Lock()

_DEFAULTS = {
    "sollwert": 22.0,
    "Kp": 40.0,
    "Ki": 10.0,
    "Kd": 0.0,
    "zykluszeit_sek": 60.0,
    "hand_modus": False,
    "hand_stellwert": 0.0,
}

GRENZEN = {
    "sollwert":        (5.0, 40.0),
    "Kp":              (0.0, 100.0),
    "Ki":              (0.0, 60.0),
    "Kd":              (0.0, 60.0),
    "zykluszeit_sek":  (10.0, 600.0),
    "hand_stellwert":  (0.0, 100.0),
}


def _laden():
    result = dict(_DEFAULTS)
    try:
        if os.path.exists(_PFAD):
            with open(_PFAD, "r", encoding="utf-8") as f:
                inhalt = f.read().strip()
            if inhalt:
                daten = json.loads(inhalt)
                result.update(daten)   # JSON-Werte überschreiben Defaults
    except Exception:
        pass
    return result


def laden():
    with _LOCK:
        return _laden()


def speichern(updates: dict):
    with _LOCK:
        aktuell = _laden()
        aktuell.update(updates)
        try:
            verzeichnis = os.path.dirname(_PFAD)
            fd, tmp = tempfile.mkstemp(dir=verzeichnis, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(aktuell, f, indent=2, ensure_ascii=False)
            os.replace(tmp, _PFAD)
        except Exception as e:
            import logging
            logging.getLogger("runtime").error("Speichern fehlgeschlagen: %s", e)


def validiere_und_speichere(updates: dict):
    for key, wert in updates.items():
        if key == "hand_modus":
            if not isinstance(wert, bool):
                return False, "'hand_modus' muss true oder false sein", {}
        elif key in GRENZEN:
            lo, hi = GRENZEN[key]
            try:
                v = float(wert)
            except (TypeError, ValueError):
                return False, f"'{key}' ist keine gültige Zahl: {wert!r}", {}
            if not (lo <= v <= hi):
                return False, f"'{key}' muss zwischen {lo} und {hi} liegen (erhalten: {v})", {}
            updates[key] = round(v, 4)
    speichern(updates)
    return True, "", laden()
