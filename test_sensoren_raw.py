"""
Rohes Modbus-RTU Test-Skript für alle 4 Temperatursensoren (22DT-15..).
Kommuniziert direkt über pyserial ohne minimalmodbus.
"""

import serial
import time

PORT = "/dev/ttySC0"
BAUDRATE = 38400
SENSOR_ADRESSEN = [1, 2, 3, 4]


def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def lese_temperatur(ser: serial.Serial, adresse: int) -> str:
    """Sendet Modbus FC03 Anfrage und liest Temperatur aus Register 0."""
    nutzdaten = bytes([adresse, 0x03, 0x00, 0x00, 0x00, 0x01])
    befehl = nutzdaten + crc16_modbus(nutzdaten)

    ser.reset_input_buffer()
    ser.write(befehl)
    time.sleep(0.2)
    antwort = ser.read(100)

    if not antwort:
        return "TIMEOUT – kein Gerät auf dieser Adresse"

    hex_str = antwort.hex(" ").upper()
    if len(antwort) >= 7:
        raw_val = int.from_bytes(antwort[3:5], byteorder="big", signed=True)
        temperatur = raw_val * 0.1
        return f"{temperatur:.1f} °C  (Antwort: {hex_str})"
    else:
        return f"Ungültige Antwort: {hex_str}"


print(f"Port: {PORT}  |  {BAUDRATE}-8N2")
print("=" * 55)

try:
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_TWO,
        bytesize=serial.EIGHTBITS,
        timeout=2,
    )
except serial.SerialException as e:
    print(f"FEHLER: Port {PORT} konnte nicht geöffnet werden: {e}")
    raise SystemExit(1)

for adresse in SENSOR_ADRESSEN:
    ergebnis = lese_temperatur(ser, adresse)
    print(f"Sensor {adresse}: {ergebnis}")

ser.close()
print("=" * 55)
