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
        from hardware.modbus_rtu import erstelle_rs485_bus
        from hardware.temperatur_sensor import TemperaturSensor
        from hardware.ventil import KaelteVentil

        logger.info("[INIT] Öffne RS-485-Bus %s …", cfg.SERIELLER_PORT)
        bus = erstelle_rs485_bus(
            port=cfg.SERIELLER_PORT,
            baudrate=cfg.BAUDRATE,
            parity=cfg.PARITAET,
            stopbits=cfg.STOPBITS,
        )
        logger.info("[INIT] Bus geöffnet. Erstelle Sensor-Instanzen …")

        sensoren = []
        for i, adr in enumerate(cfg.TEMPERATUR_SENSOR_ADRESSEN):
            logger.info("[INIT] Sensor %d (Adr %d) …", i + 1, adr)
            sensoren.append(TemperaturSensor(
                port=cfg.SERIELLER_PORT, adresse=adr,
                baudrate=cfg.BAUDRATE, parity=cfg.PARITAET,
                stopbits=cfg.STOPBITS,
                name=f"Temp-Sensor {i+1} (Adr {adr})",
                shared_serial=bus,
            ))

        logger.info("[INIT] Erstelle Ventil (Adr %d) …", cfg.VENTIL_ADRESSE)
        ventil = KaelteVentil(
            port=cfg.SERIELLER_PORT, adresse=cfg.VENTIL_ADRESSE,
            baudrate=cfg.BAUDRATE, parity=cfg.PARITAET,
            stopbits=cfg.STOPBITS, name="Kaelte-Ventil",
            shared_serial=bus,
        )
        logger.info("Hardware initialisiert (%d Sensoren, Ventil Adr %d)", len(sensoren), cfg.VENTIL_ADRESSE)
        return sensoren, ventil
    except Exception as exc:
        logger.warning("Hardware nicht erreichbar: %s", exc)
        return None, None


def lese_temperaturen(sensoren, alarmmgr, namen):
    if not sensoren:
        return [None, None, None, None]
    from hardware.modbus_rtu import BUS_PAUSE_SEK
    werte = []
    for i, sensor in enumerate(sensoren):
        logger.debug("[LESE] %s …", sensor.name)
        try:
            t = sensor.lese_temperatur()
            logger.debug("[LESE] %s = %.1f °C", sensor.name, t)
            werte.append(t)
            alarmmgr.verbindung_wiederhergestellt(namen[i])
        except Exception:
            logger.debug("[LESE] %s – kein Wert", sensor.name)
            werte.append(float("nan"))
            alarmmgr.verbindungs_abbruch(namen[i])
        time.sleep(BUS_PAUSE_SEK)
    return werte


def gueltiger_mittelwert(werte):
    gueltige = [w for w in werte if w is not None and w == w]
    if not gueltige:
        return None, 0
    return mean(gueltige), len(gueltige)


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

    import runtime_settings
    rst = runtime_settings.laden()   # Werte kommen ausschließlich aus runtime_settings.json
    sollwert = rst["sollwert"]
    Kp = rst["Kp"]
    Ki = rst["Ki"]
    Kd = rst["Kd"]

    pid = PIDRegler(Kp=Kp, Ki=Ki, Kd=Kd, kuehl_betrieb=True)  # Kälteventil: Ist > Soll → Ventil auf
    logger_datei = DatenLogger()

    logger.info("Regelung gestartet. Sollwert=%.1f°C, Kp=%.1f Ki=%.1f Kd=%.1f, Zyklus=%.0fs",
                sollwert, Kp, Ki, Kd, config.ZYKLUSZEIT_SEK)

    _einstellungen_last = 0.0
    _sollwert = sollwert
    _hand_modus = rst.get("hand_modus", False)
    _hand_stellwert = rst.get("hand_stellwert", 0.0)
    sensor_namen = ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"]
    _sensor_anzahl_last = len(sensor_namen)
    _log_last = 0.0
    _pid_letzte_zeit = time.monotonic()

    try:
        while True:
            zyklus_start = time.monotonic()
            status = "OK"

            # Betriebsart jeden Zyklus lesen (sofortige Reaktion auf Umschalten)
            rst_akt = runtime_settings.laden()
            _hand_modus = rst_akt.get("hand_modus", False)
            _hand_stellwert = rst_akt.get("hand_stellwert", 0.0)

            jetzt = time.monotonic()
            if jetzt - _einstellungen_last >= 60:
                try:
                    _sollwert = rst_akt.get("sollwert", _sollwert)
                    pid.setze_parameter(
                        Kp=rst_akt.get("Kp", pid.Kp),
                        Ki=rst_akt.get("Ki", pid.Ki),
                        Kd=rst_akt.get("Kd", pid.Kd),
                    )
                except Exception:
                    pass
                _einstellungen_last = jetzt

            temps = lese_temperaturen(sensoren, alarmmgr, sensor_namen)

            mittelwert, sensor_anzahl = gueltiger_mittelwert(temps)

            ausgabe = None
            position = None

            if _hand_modus:
                # Hand-Betrieb: PID überbrückt, direkte Stellwertvorgabe
                ausgabe = max(0.0, min(100.0, _hand_stellwert))
                status = "HAND"
            elif mittelwert is not None:
                if sensor_anzahl != _sensor_anzahl_last:
                    if sensor_anzahl < len(sensor_namen):
                        logger.warning(
                            "Nur %d/%d Sensoren online – Mittelwert %.1f °C",
                            sensor_anzahl, len(sensor_namen), mittelwert,
                        )
                    else:
                        logger.info("Alle %d Sensoren wieder online", len(sensor_namen))
                    _sensor_anzahl_last = sensor_anzahl
                ausgabe = pid.berechne(
                    sollwert=_sollwert,
                    messwert=mittelwert,
                    dt=time.monotonic() - _pid_letzte_zeit,
                )
                _pid_letzte_zeit = time.monotonic()
            else:
                if _sensor_anzahl_last != 0:
                    logger.warning("Keine Temperaturdaten – Regelung pausiert")
                    _sensor_anzahl_last = 0
                status = "KEINE_DATEN"

            if ausgabe is not None:
                if ventil is not None:
                    try:
                        ventil.setze_stellwert(ausgabe)
                        alarmmgr.verbindung_wiederhergestellt("Ventilantrieb")
                    except Exception as exc:
                        logger.error("Ventil nicht schreibbar: %s", exc)
                        alarmmgr.verbindungs_abbruch("Ventilantrieb")
                        status = "VENTIL_SCHREIBFEHLER"
                    time.sleep(0.08)   # Antrieb Zeit geben, Paket zu verarbeiten
                    try:
                        position = ventil.lese_position()
                    except Exception as exc:
                        logger.error("Ventilposition nicht lesbar: %s", exc)
                        alarmmgr.verbindungs_abbruch("Ventilantrieb")
                        status = status if status != "OK" else "VENTIL_LESEFEHLER"
                if position is None:
                    position = float("nan")

            # Live-Daten sofort für das Dashboard bereitstellen (alle 3 s)
            try:
                import web_server as _ws
                _ws.setze_live_daten({
                    "zeitstempel": __import__('datetime').datetime.now().isoformat(timespec="seconds"),
                    "temp_sensor_1": temps[0] if len(temps) > 0 else None,
                    "temp_sensor_2": temps[1] if len(temps) > 1 else None,
                    "temp_sensor_3": temps[2] if len(temps) > 2 else None,
                    "temp_sensor_4": temps[3] if len(temps) > 3 else None,
                    "temp_mittelwert": mittelwert,
                    "pid_ausgabe_prozent": ausgabe,
                    "ventil_position_prozent": position,
                    "status": status,
                    "hand_modus": _hand_modus,
                    "hand_stellwert": _hand_stellwert,
                })
            except Exception:
                pass

            logger.debug(
                "[ZYKLUS] Temp=%.1f°C Soll=%.1f°C PID->%.1f%% Ventil-Ist=%.1f%% [%s]",
                mittelwert if mittelwert is not None else float('nan'),
                _sollwert,
                ausgabe if ausgabe is not None else float('nan'),
                position if (position is not None and position == position) else float('nan'),
                status,
            )

            if time.monotonic() - _log_last >= 60.0:
                logger_datei.schreibe_zeile(
                    temps=temps, mittelwert=mittelwert,
                    sollwert=_sollwert if (mittelwert is not None or _hand_modus) else None,
                    ausgabe=ausgabe, ventil_position=position, status=status,
                    hand_modus=_hand_modus,
                )
                _log_last = time.monotonic()

            wartezeit = config.ZYKLUSZEIT_SEK - (time.monotonic() - zyklus_start)
            time.sleep(max(0.0, wartezeit))

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
