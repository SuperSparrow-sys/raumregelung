"""
Ansteuerung eines Belimo Temperaturfühlers (22DT-15..) über Modbus RTU.

Laut Datenblatt "Sensor_Modbus-Register_en_V0_1.pdf":
    Register 0 (Adr 0): Temperatur, Skalierungsfaktor 0.1, signed, Einheit °C
"""

from hardware.modbus_rtu import ModbusRTUGeraet

REGISTER_TEMPERATUR = 0
DEZIMALSTELLEN_TEMPERATUR = 1  # Skalierungsfaktor 0.1


class TemperaturSensor(ModbusRTUGeraet):
    """Ein Belimo Raum-/Kanaltemperaturfühler (22DT-15..) mit Modbus RTU."""

    def lese_temperatur(self) -> float:
        """Liest die aktuelle Temperatur in °C."""
        return self.lese_register(
            REGISTER_TEMPERATUR,
            anzahl_dezimalstellen=DEZIMALSTELLEN_TEMPERATUR,
            signed=True,
        )
