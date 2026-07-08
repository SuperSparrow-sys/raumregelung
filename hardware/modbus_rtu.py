"""
Gemeinsame Modbus-RTU Basisfunktionen für die serielle Kommunikation
mit Belimo Sensoren und Aktoren (RS-485).

Busarchitektur: Ein gemeinsamer serieller Port (RS-485, 8E1, RTS-Richtungssteuerung)
wird von allen Geräten geteilt. Erzeugung via erstelle_rs485_bus().

Benötigt die Bibliothek 'minimalmodbus':
    pip install minimalmodbus
"""

import logging
import time

import minimalmodbus
import serial
from serial.rs485 import RS485Settings

logger = logging.getLogger("modbus_rtu")

_PARITAET_MAP = {
    "N": serial.PARITY_NONE,
    "E": serial.PARITY_EVEN,
    "O": serial.PARITY_ODD,
}

BUS_PAUSE_SEK = 0.05   # Mindestpause zwischen zwei Bustelegrammen


def erstelle_rs485_bus(port: str, baudrate: int = 38400,
                       parity: str = "E", stopbits: int = 1,
                       timeout: float = 0.2) -> serial.Serial:
    """Öffnet den RS-485-Bus einmalig – exakt wie test_ventil_raw.py.

    Port wird über minimalmodbus.Instrument geöffnet, dessen .serial
    anschließend von allen Geräten gemeinsam genutzt wird.
    """
    base = minimalmodbus.Instrument(port, slaveaddress=1)
    base.serial.baudrate = baudrate
    base.serial.bytesize = 8
    base.serial.parity   = _PARITAET_MAP[parity]
    base.serial.stopbits = stopbits
    base.serial.timeout  = timeout
    base.mode            = minimalmodbus.MODE_RTU
    base.serial.rs485_mode = RS485Settings(
        rts_level_for_tx=True,
        rts_level_for_rx=False,
        delay_before_tx=0.0,
        delay_before_rx=0.0,
    )
    logger.info("RS-485-Bus geöffnet: %s (%d Bd, 8%s%d)", port, baudrate, parity, stopbits)
    return base.serial


class ModbusRTUGeraet:
    """Basisklasse für ein Modbus-RTU Gerät (Sensor oder Aktor).

    Bevorzugt shared_serial verwenden (erstellt via erstelle_rs485_bus()),
    damit alle Geräte denselben RS-485-Port teilen und der Port nicht bei
    jeder Transaktion geöffnet/geschlossen wird.
    """

    def __init__(self, port: str, adresse: int, baudrate: int = 38400,
                 parity: str = "E", stopbits: int = 1, bytesize: int = 8,
                 timeout: float = 0.2, name: str = "",
                 shared_serial: serial.Serial = None):
        """
        Args:
            port:          Serieller Port (nur für Fallback ohne shared_serial)
            adresse:       Modbus-Slave-Adresse (1...247)
            baudrate:      Übertragungsrate
            parity:        "N", "E" oder "O"
            stopbits:      1 oder 2
            bytesize:      Datenbits (immer 8)
            timeout:       Antwort-Timeout in Sekunden
            name:          Klartextname für Logausgaben
            shared_serial: Gemeinsames Serial-Objekt vom RS-485-Bus.
                           Wenn angegeben, wird der Port NICHT separat geöffnet.
        """
        self.name = name or f"Geraet@{adresse}"
        self.adresse = adresse

        # Exakt wie Referenzskript: Instrument ohne mode-Parameter erstellen
        self.instrument = minimalmodbus.Instrument(port, slaveaddress=adresse)

        if shared_serial is not None:
            # Serial direkt ersetzen – exakt wie Referenzskript
            self.instrument.serial = shared_serial
        else:
            # Fallback ohne shared_serial
            self.instrument.serial.baudrate = baudrate
            self.instrument.serial.bytesize = bytesize
            self.instrument.serial.parity   = _PARITAET_MAP[parity]
            self.instrument.serial.stopbits = stopbits
            self.instrument.serial.timeout  = timeout
            self.instrument.serial.rs485_mode = RS485Settings(
                rts_level_for_tx=True,
                rts_level_for_rx=False,
                delay_before_tx=0.0,
                delay_before_rx=0.0,
            )

    def lese_register(self, register: int, anzahl_dezimalstellen: int = 0,
                       signed: bool = False, versuche: int = 3):
        """Liest ein Holding-Register (Funktion 03), mit Wiederholung bei Fehlern.

        anzahl_dezimalstellen entspricht dem Skalierungsfaktor der Registerbeschreibung
        (z.B. Skalierungsfaktor 0.1 -> anzahl_dezimalstellen=1).
        """
        letzter_fehler = None
        for versuch in range(1, versuche + 1):
            try:
                logger.debug("%s: lese Reg %d (Versuch %d) …", self.name, register, versuch)
                wert = self.instrument.read_register(
                    register,
                    number_of_decimals=anzahl_dezimalstellen,
                    functioncode=3,
                    signed=signed,
                )
                logger.debug("%s: Reg %d = %s", self.name, register, wert)
                return wert
            except Exception as exc:
                letzter_fehler = exc
                logger.warning("%s: Lesefehler Register %d (Versuch %d/%d): %s",
                                self.name, register, versuch, versuche, exc)
                time.sleep(0.1)
        raise ConnectionError(
            f"{self.name}: Register {register} nach {versuche} Versuchen nicht lesbar"
        ) from letzter_fehler

    def schreibe_register(self, register: int, wert, anzahl_dezimalstellen: int = 0,
                           signed: bool = False, versuche: int = 3):
        """Schreibt ein Holding-Register (Funktion 06), mit Wiederholung bei Fehlern."""
        letzter_fehler = None
        for versuch in range(1, versuche + 1):
            try:
                logger.debug("%s: schreibe Reg %d = %s (Versuch %d) …",
                             self.name, register, wert, versuch)
                self.instrument.write_register(
                    register,
                    wert,
                    number_of_decimals=anzahl_dezimalstellen,
                    functioncode=6,
                    signed=signed,
                )
                logger.debug("%s: Reg %d geschrieben", self.name, register)
                return
            except Exception as exc:
                letzter_fehler = exc
                logger.warning("%s: Schreibfehler Register %d (Versuch %d/%d): %s",
                                self.name, register, versuch, versuche, exc)
                time.sleep(0.1)
        raise ConnectionError(
            f"{self.name}: Register {register} nach {versuche} Versuchen nicht schreibbar"
        ) from letzter_fehler
