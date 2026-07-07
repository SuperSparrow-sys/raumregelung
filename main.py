import logging
import time
import threading
from statistics import mean

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("main")


def _starte_webserver():
    try:
        import web_server
        web_server.app.run(host="0.0.0.0", port=5050, debug=False, threaded=True, use_reloader=False)
    except Exception as exc:
        logger.error("Web-Server fehlgeschlagen: %s", exc)


def _versuche_hardware():
    try:
        import config as cfg
        from hardware.temperatur_sensor import TemperaturSensor
        from hardware.ventil import KaelteVentil
        sensoren = [
            TemperaturSensor(
                port=cfg.SERIELLER_PORT, adresse=adr,
                baudrate=cfg.BAUDRATE, parity=cfg.PARITAET,
                stopbits=cfg.STOPBITS,
                name=f"Temp-Sensor {i+1} (Adr {adr})",
            )
            for i, adr in enumerate(cfg.TEMPERATUR_SENSOR_ADRESSEN)
        ]
        ventil = KaelteVentil(
            port=cfg.SERIELLER_PORT, adresse=cfg.VENTIL_ADRESSE,
            baudrate=cfg.BAUDRATE, parity=cfg.PARITAET,
            stopbits=cfg.STOPBITS, name="Kaelte-Ventil",
        )
        logger.info("Hardware initialisiert (%d Sensoren, Ventil Adr %d)", len(sensoren), cfg.VENTIL_ADRESSE)
        return sensoren, ventil
    except Exception as exc:
        logger.warning("Hardware nicht erreichbar: %s", exc)
        return None, None


def lese_temperaturen(sensoren, alarmmgr, namen):
    if not sensoren:
        return [None, None, None, None]
    werte = []
    for i, sensor in enumerate(sensoren):
        try:
            t = sensor.lese_temperatur()
            werte.append(t)
            alarmmgr.verbindung_wiederhergestellt(namen[i])
        except Exception as exc:
            logger.error("Sensor %s nicht lesbar: %s", sensor.name, exc)
            werte.append(float("nan"))
            alarmmgr.verbindungs_abbruch(namen[i])
    return werte


def gueltiger_mittelwert(werte):
    gueltige = [w for w in werte if w is not None and w == w]
    if not gueltige:
        return None
    return mean(gueltige)


def main():
    logger.info("Starte Web-Server …")
    web_thread = threading.Thread(target=_starte_webserver, daemon=True)
    web_thread.start()
    time.sleep(0.5)

    try:
        import config
    except Exception as exc:
        logger.critical("config.py konnte nicht geladen werden: %s", exc)
        while True:
            time.sleep(10)

    from control.alarmmanager import AlarmManager
    alarmmgr = AlarmManager()
    logger_datei = None
    sensoren, ventil = _versuche_hardware()
    if sensoren is None:
        logger.warning("Keine Hardware – Regelung läuft mit Nullwerten")
        for name in ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4", "Ventilantrieb"]:
            alarmmgr.verbindungs_abbruch(name)
        sensoren = []
        ventil = None

    from control.pid_regler import PIDRegler
    from data.datenlogger import DatenLogger

    try:
        import runtime_settings
        rst = runtime_settings.laden()
        sollwert = rst.get("sollwert", config.SOLLWERT_TEMPERATUR)
        Kp = rst.get("Kp", config.PID_KP)
        Ki = rst.get("Ki", config.PID_KI)
        Kd = rst.get("Kd", config.PID_KD)
    except Exception:
        sollwert = config.SOLLWERT_TEMPERATUR
        Kp = config.PID_KP
        Ki = config.PID_KI
        Kd = config.PID_KD

    pid = PIDRegler(Kp=Kp, Ki=Ki, Kd=Kd)
    logger_datei = DatenLogger()

    logger.info("Regelung gestartet. Sollwert=%.1f°C, Kp=%.1f Ki=%.1f Kd=%.1f, Zyklus=%.0fs",
                sollwert, Kp, Ki, Kd, config.ZYKLUSZEIT_SEK)

    _einstellungen_last = 0.0
    _sollwert = sollwert
    sensor_namen = ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"]

    try:
        while True:
            zyklus_start = time.monotonic()
            status = "OK"

            jetzt = time.monotonic()
            if jetzt - _einstellungen_last >= 60:
                try:
                    rst = runtime_settings.laden()
                    _sollwert = rst.get("sollwert", _sollwert)
                    pid.setze_parameter(
                        Kp=rst.get("Kp", Kp),
                        Ki=rst.get("Ki", Ki),
                        Kd=rst.get("Kd", Kd),
                    )
                except Exception:
                    pass
                _einstellungen_last = jetzt

            temps = lese_temperaturen(sensoren, alarmmgr, sensor_namen)

            mittelwert = gueltiger_mittelwert(temps)

            if mittelwert is not None:
                ausgabe = pid.berechne(
                    sollwert=_sollwert,
                    messwert=mittelwert,
                    dt=config.ZYKLUSZEIT_SEK,
                )
                position = None
                if ventil is not None:
                    try:
                        ventil.setze_stellwert(ausgabe)
                        alarmmgr.verbindung_wiederhergestellt("Ventilantrieb")
                    except Exception as exc:
                        logger.error("Ventil nicht schreibbar: %s", exc)
                        alarmmgr.verbindungs_abbruch("Ventilantrieb")
                        status = "VENTIL_SCHREIBFEHLER"
                    try:
                        position = ventil.lese_position()
                    except Exception as exc:
                        logger.error("Ventilposition nicht lesbar: %s", exc)
                        alarmmgr.verbindungs_abbruch("Ventilantrieb")
                        status = status if status != "OK" else "VENTIL_LESEFEHLER"
                if position is None:
                    position = float("nan")
                logger.info(
                    "Temp=%.2f°C (Soll=%.1f°C) → PID=%.1f%% → Ventil=%.1f%% [%s]",
                    mittelwert, _sollwert, ausgabe, position, status,
                )
            else:
                ausgabe = None
                position = None
                logger.warning("Keine Temperaturdaten – Regelung pausiert")

            logger_datei.schreibe_zeile(
                temps=temps, mittelwert=mittelwert,
                sollwert=_sollwert if mittelwert is not None else None,
                ausgabe=ausgabe, ventil_position=position, status=status,
            )

            wartezeit = config.ZYKLUSZEIT_SEK - (time.monotonic() - zyklus_start)
            time.sleep(max(1.0, wartezeit))

    except KeyboardInterrupt:
        logger.info("Regelung durch Benutzer beendet.")
    except Exception:
        logger.exception("Unerwarteter Fehler in der Hauptschleife")
    finally:
        if ventil is not None:
            try:
                ventil.setze_stellwert(0.0)
            except Exception:
                pass
        if logger_datei is not None:
            logger_datei.schliessen()


if __name__ == "__main__":
    main()
