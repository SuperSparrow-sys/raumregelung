import time
from hardware.temperatur_sensor import TemperaturSensor

PORT = "/dev/serial0"
ADRESSE = 1
BAUDRATE = 38400
PARITY = "N"
STOPBITS = 2

sensor = TemperaturSensor(
    port=PORT,
    adresse=ADRESSE,
    baudrate=BAUDRATE,
    parity=PARITY,
    stopbits=STOPBITS,
    name="Test-Sensor"
)

print(f"Lese Sensor (Adr {ADRESSE}) alle 5 s ...")

while True:
    try:
        temp = sensor.lese_temperatur()
        print(f"[{time.strftime('%H:%M:%S')}] Temperatur: {temp:.1f} C")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Fehler: {e}")
    time.sleep(5)
