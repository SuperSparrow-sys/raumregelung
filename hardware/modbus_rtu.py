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
    """Öffnet den RS-485-Bus einmalig und gibt das konfigurierte Serial-Objekt zurück.

    Alle Modbus-Geräte am selben Bus teilen sich dieses Objekt (shared serial).
    Die RTS-Richtungssteuerung wird über RS485Settings aktiviert.

    Args:
        port:     Serieller Port, z.B. "/dev/ttySC1" oder "COM3"
        baudrate: Übertragungsrate (Belimo-Standard: 38400)
        parity:   "E" für Even – Belimo-Standard (8E1)
        stopbits: 1  – Belimo-Standard bei Even-Parität
        timeout:  Antwort-Timeout in Sekunden
    """
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        parity=_PARITAET_MAP[parity],
        stopbits=stopbits,
        timeout=timeout,
    )
    # RTS-basierte Senderichtungssteuerung für den RS-485-Transceiver
    ser.rs485_mode = RS485Settings(
        rts_level_for_tx=True,
        rts_level_for_rx=False,
        delay_before_tx=0.0,
        delay_before_rx=0.0,
    )
    logger.info("RS-485-Bus geöffnet: %s (%d Bd, 8%s%d)", port, baudrate, parity, stopbits)
    return ser


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

        self.instrument = minimalmodbus.Instrument(
            port, adresse, mode=minimalmodbus.MODE_RTU
        )
        self.instrument.clear_buffers_before_each_transaction = True

        if shared_serial is not None:
            # Temporäre Eigenverbindung von minimalmodbus sofort schließen,
            # damit kein konkurrierender Handle auf dem Port verbleibt.
            self.instrument.serial.close()
            self.instrument.serial = shared_serial
            self.instrument.close_port_after_each_call = False
        else:
            # Fallback: eigene Verbindung (Port wird je Transaktion geöffnet/geschlossen)
            self.instrument.serial.baudrate = baudrate
            self.instrument.serial.bytesize = bytesize
            self.instrument.serial.parity = _PARITAET_MAP[parity]
            self.instrument.serial.stopbits = stopbits
            self.instrument.serial.timeout = timeout
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
