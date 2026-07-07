import time
from hardware.temperatur_sensor import TemperaturSensor
from hardware.ventil import KaelteVentil

PORTS = ["/dev/ttySC0"]
BAUDRATE = 38400
PARITY = "N"
STOPBITS = 2

# --- Sensor Adresse 1, Register 0-2 ---
sensoren = {}
for port in PORTS:
    try:
        sensoren[port] = TemperaturSensor(
            port=port,
            adresse=1,
            baudrate=BAUDRATE,
            parity=PARITY,
            stopbits=STOPBITS,
            name=f"Test-Sensor ({port})"
        )
        print(f"Sensor  Port {port}: OK (geöffnet)")
    except Exception as e:
        print(f"Sensor  Port {port}: FEHLER beim Öffnen – {e}")

# --- Ventil Adresse 5, Register 4-6 ---
ventile = {}
for port in PORTS:
    try:
        ventile[port] = KaelteVentil(
            port=port,
            adresse=5,
            baudrate=BAUDRATE,
            parity=PARITY,
            stopbits=STOPBITS,
            name=f"Test-Ventil ({port})"
        )
        print(f"Ventil  Port {port}: OK (geöffnet)")
    except Exception as e:
        print(f"Ventil  Port {port}: FEHLER beim Öffnen – {e}")

print("\nLese Sensor (Adr 1, Reg 0-2) und Ventil (Adr 5, Reg 4-6) alle 5 s ...\n")

while True:
    ts = time.strftime('%H:%M:%S')

    for port, sensor in sensoren.items():
        print(f"[{ts}] === Sensor {port} (Adr 1) ===")
        for reg in [0, 1, 2]:
            try:
                wert = sensor.lese_register(reg, anzahl_dezimalstellen=0, signed=True)
                print(f"[{ts}]   Register {reg}: {wert}")
            except Exception as e:
                print(f"[{ts}]   Register {reg} Fehler: {e}")

    for port, ventil in ventile.items():
        print(f"[{ts}] === Ventil {port} (Adr 5) ===")
        for reg in [4, 5, 6]:
            try:
                rohwert = ventil.lese_register(reg, anzahl_dezimalstellen=0, signed=False)
                if reg == 4:
                    print(f"[{ts}]   Register {reg} (Rel. Position): {rohwert} (= {rohwert / 100:.1f} %)")
                else:
                    print(f"[{ts}]   Register {reg}: {rohwert}")
            except Exception as e:
                print(f"[{ts}]   Register {reg} Fehler: {e}")

    print("---")
    time.sleep(5)
