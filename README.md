# Kälte-Regelung – PID auf Mittelwert von 4 Raumtemperaturfühlern

Regelt ein Belimo Kälte-Ventil (SR24A-MOD, Modbus RTU) auf den Mittelwert von
4 Belimo Raumtemperaturfühlern (22DT-15.., Modbus RTU), alle an einem
gemeinsamen RS-485 Bus.

## Dateien

| Datei                 | Zweck                                                              |
|------------------------|---------------------------------------------------------------------|
| `modbus_rtu.py`        | Basisklasse für Modbus-RTU Lesen/Schreiben mit Wiederholungslogik  |
| `temperatur_sensor.py` | Klasse `TemperaturSensor` (Register 0, 22DT-15..)                  |
| `ventil.py`            | Klasse `KaelteVentil` (Register 0/4/104, SR24A-MOD)                |
| `pid_regler.py`        | Dein PID-Regler mit Anti-Windup (Kp / Ki[min] / Kd[min])            |
| `datenlogger.py`       | Schreibt jede Regelzyklus-Zeile in eine CSV-Datei                  |
| `config.py`            | Alle anlagenspezifischen Einstellungen (Port, Adressen, PID, ...)  |
| `main.py`              | Hauptprogramm / Regelschleife                                      |
| `requirements.txt`     | Benötigte Python-Pakete                                             |

## Installation

```bash
pip install -r requirements.txt
```

## Verdrahtung (RS-485, alle Geräte am selben Bus)

- Sensor 22DT-15..: Klemmen `B(A) / A(D+) / GND / UB+` — siehe Datenblatt Seite 3.
- Ventil SR24A-MOD: Klemmen `3=D-(A) / 5=D+(B) / 6/7=Y(Sensor)` — Modbus-Zuordnung
  laut Datenblatt: `C1 = D- = A`, `C2 = D+ = B`.
- A an A, B an B, GND an GND durchverbinden, am Busende ggf. 120 Ohm
  Abschlusswiderstand (beim Ventil zuschaltbar).

## Vor dem ersten Start anpassen (`config.py`)

1. **`SERIELLER_PORT`** – z. B. `/dev/ttyUSB0` (Linux) oder `COM3` (Windows).
2. **`BAUDRATE` / `PARITAET` / `STOPBITS`** – müssen mit den DIP-Schalter-
   Einstellungen der 4 Sensoren (DIP2) und der ZTH-EU-Parametrierung des
   Ventils übereinstimmen. Werkseinstellung beider Geräte: 38400 Bd, 1-8-N-2.
3. **`TEMPERATUR_SENSOR_ADRESSEN`** – die 4 per DIP1 eingestellten
   Modbus-Adressen der Fühler (1…247).
4. **`VENTIL_ADRESSE`** – die per ZTH EU oder Schnelladressierung
   eingestellte Adresse des Ventils.
5. **`SOLLWERT_TEMPERATUR`**, **`PID_KP` / `PID_KI` / `PID_KD`** – Regelparameter
   nach Bedarf einstellen/optimieren.

## Start

```bash
python main.py
```

Die Regelung läuft in einer Endlosschleife (Standard: alle 60 Sekunden ein
Zyklus), protokolliert jeden Zyklus in `regelung_log.csv` und wird mit
`Strg+C` sauber beendet (Ventil wird dabei auf 0 % gesetzt).

## Wirkungsrichtung Kühlen (wichtig!)

Der bereitgestellte PID-Regler berechnet intern `fehler = sollwert − messwert`
(Ausgabe steigt, wenn der Messwert unter dem Sollwert liegt – das ist eine
Heiz-Logik). Für ein Kälte-Ventil muss die Ausgabe aber steigen, wenn die
Raumtemperatur **über** dem Sollwert liegt. Deshalb werden in `main.py` beim
Aufruf `sollwert` und `messwert` bewusst vertauscht (Kommentar im Code).
Falls du den Regler auch für eine Heizanwendung nutzen willst, einfach die
Argumente wieder in der ursprünglichen Reihenfolge übergeben.

## Hinweise / Grenzen

- Register < 100 beim Ventil ("In Betrieb", z. B. Sollwert) sind **flüchtig**
  und werden daher – wie vom SR24A-MOD-Datenblatt gefordert – jeden Zyklus
  neu geschrieben.
- Wird innerhalb von 120 s weder Sollwert noch Override-Register beschrieben,
  fährt das Ventil je nach Parametrierung (Register 109) in die
  Bus-Fail-Position. Bei einer Zykluszeit von 60 s ist das unkritisch.
- Fällt ein einzelner Temperaturfühler aus, wird er als NaN geloggt und aus
  der Mittelwertbildung ausgeschlossen; erst wenn alle 4 Fühler ausfallen,
  wird der Zyklus übersprungen und das Ventil bleibt auf dem letzten Wert.
- Die Skalierung `Register 1 = 0…10000 entspricht 0…100 %` und
  `Temperatur-Skalierungsfaktor 0.1` stammen direkt aus den beiden
  hochgeladenen Datenblättern.
