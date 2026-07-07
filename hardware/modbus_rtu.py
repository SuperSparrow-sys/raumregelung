"""
Gemeinsame Modbus-RTU Basisfunktionen für die serielle Kommunikation
mit Belimo Sensoren und Aktoren (RS-485).

Benötigt die Bibliothek 'minimalmodbus':
    pip install minimalmodbus
"""

import logging
import time

import minimalmodbus
import serial

logger = logging.getLogger("modbus_rtu")

_PARITAET_MAP = {
    "N": serial.PARITY_NONE,
    "E": serial.PARITY_EVEN,
    "O": serial.PARITY_ODD,
}


class ModbusRTUGeraet:
    """Basisklasse für ein Modbus-RTU Gerät (Sensor oder Aktor).

    Jede Instanz öffnet die serielle Schnittstelle über 'minimalmodbus'.
    Mehrere Geräte am selben Bus (gleicher Port) können unabhängig
    voneinander instanziert werden, da minimalmodbus den Port bei Bedarf
    für jede Transaktion neu öffnet/schließt.
    """

    def __init__(self, port: str, adresse: int, baudrate: int = 38400,
                 parity: str = "N", stopbits: int = 2, bytesize: int = 8,
                 timeout: float = 1.0, name: str = ""):
        """
        Args:
            port: serielle Schnittstelle, z.B. "/dev/ttyUSB0" oder "COM3"
            adresse: Modbus-Slave-Adresse (1...247)
            baudrate: Übertragungsrate (Belimo Werkseinstellung: 38400)
            parity: "N", "E" oder "O"
            stopbits: 1 oder 2 (bei parity="N" Werkseinstellung: 2)
            bytesize: Datenbits (immer 8)
            timeout: Antwort-Timeout in Sekunden
            name: Klartextname für Logausgaben
        """
        self.name = name or f"Geraet@{adresse}"
        self.adresse = adresse

        self.instrument = minimalmodbus.Instrument(
            port, adresse, mode=minimalmodbus.MODE_RTU
        )
        self.instrument.serial.baudrate = baudrate
        self.instrument.serial.bytesize = bytesize
        self.instrument.serial.parity = _PARITAET_MAP[parity]
        self.instrument.serial.stopbits = stopbits
        self.instrument.serial.timeout = timeout
        self.instrument.clear_buffers_before_each_transaction = True
        self.instrument.close_port_after_each_call = True

    def lese_register(self, register: int, anzahl_dezimalstellen: int = 0,
                       signed: bool = False, versuche: int = 3):
        """Liest ein Holding-Register (Funktion 03), mit Wiederholung bei Fehlern.

        anzahl_dezimalstellen entspricht dem Skalierungsfaktor der Registerbeschreibung
        (z.B. Skalierungsfaktor 0.1 -> anzahl_dezimalstellen=1).
        """
        letzter_fehler = None
        for versuch in range(1, versuche + 1):
            try:
                return self.instrument.read_register(
                    register,
                    number_of_decimals=anzahl_dezimalstellen,
                    functioncode=3,
                    signed=signed,
                )
            except (minimalmodbus.NoResponseError,
                    minimalmodbus.InvalidResponseError,
                    serial.SerialException) as exc:
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
                self.instrument.write_register(
                    register,
                    wert,
                    number_of_decimals=anzahl_dezimalstellen,
                    functioncode=6,
                    signed=signed,
                )
                return
            except (minimalmodbus.NoResponseError,
                    minimalmodbus.InvalidResponseError,
                    serial.SerialException) as exc:
                letzter_fehler = exc
                logger.warning("%s: Schreibfehler Register %d (Versuch %d/%d): %s",
                                self.name, register, versuch, versuche, exc)
                time.sleep(0.1)
        raise ConnectionError(
            f"{self.name}: Register {register} nach {versuche} Versuchen nicht schreibbar"
        ) from letzter_fehler
