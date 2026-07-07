"""
Ansteuerung eines Belimo Kälte-Ventilantriebs (SR24A-MOD) über Modbus RTU.

Laut Datenblatt "1436352736731.pdf" (Modbus Kommunikationsparameter):
    Register 1 (Adr 0):  Setpoint          0...10000 entspricht 0...100 %
    Register 2 (Adr 1):  Override control  0=None 1=Open 2=Close 3=Min 5=Max
    Register 5 (Adr 4):  Relative position 0...10000 entspricht 0...100 %
    Register 105 (Adr104): Störungs-/Servicemeldungen (Bitmaske)

Hinweis: Register <100 ("In Betrieb") sind flüchtig (volatile) und müssen
daher periodisch neu geschrieben werden - genau das übernimmt main.py im
minütlichen Regelzyklus.
"""

from hardware.modbus_rtu import ModbusRTUGeraet

REGISTER_SOLLWERT = 0
REGISTER_OVERRIDE = 1
REGISTER_RELATIVE_POSITION = 4
REGISTER_STOERUNG = 104

NICHT_UNTERSTUETZT = 65535  # Kennwert lt. Datenblatt, falls Wert nicht verfügbar


class KaelteVentil(ModbusRTUGeraet):
    """Belimo Kälte-Ventilantrieb (SR24A-MOD) mit Modbus RTU Interface."""

    def setze_stellwert(self, prozent: float):
        """Setzt den Stellwert (Ventilöffnung) in Prozent (0...100).

        Das Register erwartet 0...10000 (Hundertstel Prozent).
        """
        prozent = max(0.0, min(100.0, prozent))
        rohwert = int(round(prozent * 100))  # 0..10000
        self.schreibe_register(
            REGISTER_SOLLWERT, rohwert, anzahl_dezimalstellen=0, signed=False
        )

    def lese_position(self) -> float:
        """Liest die aktuelle relative Ventilstellung in Prozent (0...100)."""
        rohwert = self.lese_register(
            REGISTER_RELATIVE_POSITION, anzahl_dezimalstellen=0, signed=False
        )
        if rohwert == NICHT_UNTERSTUETZT:
            return float("nan")
        return rohwert / 100.0

    def lese_stoerung(self) -> int:
        """Liest das Störungs-/Service-Register (Bitmaske, siehe Datenblatt Seite 6)."""
        return self.lese_register(
            REGISTER_STOERUNG, anzahl_dezimalstellen=0, signed=False
        )

    def schliessen_sofort(self):
        """Override-Control 'Close' setzen -> Ventil fährt sofort zu (z.B. bei Not-Stop)."""
        self.schreibe_register(REGISTER_OVERRIDE, 2, anzahl_dezimalstellen=0, signed=False)

    def override_aufheben(self):
        """Override-Control zurück auf 'None' -> normale Sollwert-Regelung aktiv."""
        self.schreibe_register(REGISTER_OVERRIDE, 0, anzahl_dezimalstellen=0, signed=False)
