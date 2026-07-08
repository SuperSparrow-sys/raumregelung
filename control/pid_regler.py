"""
PID-Regler mit Anti-Windup.

Eingabe der Zeitanteile in **Sekunden**:
  Kp  – Proportionalverstaerkung (dimensionslos)
  Ki  – Nachstellzeit I-Anteil in Sekunden  (0 = kein I-Anteil)
  Kd  – Vorhaltezeit  D-Anteil in Sekunden  (0 = kein D-Anteil)

Anti-Windup: Integral wird so begrenzt, dass der I-Anteil allein
maximal ±AUSGABE_MAX erreichen kann.
"""

AUSGABE_MAX = 100.0   # Stellgroesse-Obergrenze (%)
AUSGABE_MIN = 0.0     # Stellgroesse-Untergrenze (%)


class PIDRegler:
    """PID-Regler – Eingabe Ki/Kd in Sekunden, Anti-Windup.

    kuehl_betrieb=True:  Fehler = Ist − Soll  (Ventil öffnet wenn zu warm)
    kuehl_betrieb=False: Fehler = Soll − Ist  (Ventil öffnet wenn zu kalt)
    """

    def __init__(self, Kp: float, Ki: float, Kd: float, kuehl_betrieb: bool = False):
        """
        Args:
            Kp:            Proportionalverstaerkung
            Ki:            I-Anteil in Sekunden (0 = aus)
            Kd:            D-Anteil in Sekunden (0 = aus)
            kuehl_betrieb: True für Kälteventil (Ist > Soll → mehr Kühlen)
        """
        self.Kp = Kp
        self.Ki = Ki   # Sekunden
        self.Kd = Kd   # Sekunden
        self.kuehl_betrieb = kuehl_betrieb

        # Interne Zustandsvariablen
        self.integral = 0.0
        self.letzter_fehler = 0.0
        self.letzte_zeit = None

    # ----- Ki/Kd werden direkt in Sekunden verwendet -----
    @property
    def _ki_sek(self) -> float:
        """Ki in 1/s: Kp / Ki_sek.  0 wenn Ki == 0."""
        if self.Ki <= 0:
            return 0.0
        return self.Kp / self.Ki

    @property
    def _kd_sek(self) -> float:
        """Kd in s: Kp * Kd_sek."""
        return self.Kp * self.Kd

    def berechne(self, sollwert: float, messwert: float, dt: float = 1.0) -> float:
        """
        Berechnet die PID-Stellgroesse.

        Args:
            sollwert: Sollwert
            messwert: Gemessener Istwert
            dt: Zeitschritt in Sekunden (Standard: 1.0)

        Returns:
            Stellgroesse (immer auf [0, 100] begrenzt)
        """
        fehler = (messwert - sollwert) if self.kuehl_betrieb else (sollwert - messwert)

        # P
        P = self.Kp * fehler

        # I  (mit Anti-Windup via Back-Calculation)
        ki_s = self._ki_sek
        if ki_s > 0:
            self.integral += fehler * dt
            I = ki_s * self.integral
        else:
            I = 0.0

        # D
        kd_s = self._kd_sek
        if kd_s > 0 and dt > 0:
            ableitung = (fehler - self.letzter_fehler) / dt
            D = kd_s * ableitung
        else:
            D = 0.0

        self.letzter_fehler = fehler

        ausgabe = P + I + D

        # Anti-Windup: Wenn Ausgabe an Grenze, Integral zurueckrechnen
        # damit der I-Anteil nicht ueber die Grenze hinaus akkumuliert.
        if ki_s > 0:
            if ausgabe > AUSGABE_MAX:
                self.integral = (AUSGABE_MAX - P - D) / ki_s
                ausgabe = AUSGABE_MAX
            elif ausgabe < AUSGABE_MIN:
                self.integral = (AUSGABE_MIN - P - D) / ki_s
                ausgabe = AUSGABE_MIN

        return ausgabe

    def zuruecksetzen(self):
        """Setzt Integral und letzten Fehler zurueck."""
        self.integral = 0.0
        self.letzter_fehler = 0.0
        self.letzte_zeit = None

    def setze_parameter(self, Kp: float = None, Ki: float = None, Kd: float = None):
        """Aktualisiert PID-Parameter (Ki/Kd in Sekunden)."""
        if Kp is not None:
            self.Kp = Kp
        if Ki is not None:
            self.Ki = Ki
        if Kd is not None:
            self.Kd = Kd
