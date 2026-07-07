import time
from hardware.temperatur_sensor import TemperaturSensor

PORTS = ["/dev/serial0", "/dev/ttyAMA10"]
ADRESSE = 1
BAUDRATE = 38400
PARITY = "N"
STOPBITS = 2

sensoren = {}
for port in PORTS:
    try:
        sensoren[port] = TemperaturSensor(
            port=port,
            adresse=ADRESSE,
            baudrate=BAUDRATE,
            parity=PARITY,
            stopbits=STOPBITS,
            name=f"Test-Sensor ({port})"
        )
        print(f"Port {port}: OK (geöffnet)")
    except Exception as e:
        print(f"Port {port}: FEHLER beim Öffnen – {e}")

print(f"\nLese Sensor (Adr {ADRESSE}) alle 5 s ...\n")

while True:
    ts = time.strftime('%H:%M:%S')
    for port, sensor in sensoren.items():
        print(f"[{ts}] === {port} ===")
        for reg in [0, 1, 2]:
            try:
                wert = sensor.lese_register(reg, anzahl_dezimalstellen=0, signed=True)
                print(f"[{ts}]   Register {reg}: {wert}")
            except Exception as e:
                print(f"[{ts}]   Register {reg} Fehler: {e}")
    print("---")
    time.sleep(5)
