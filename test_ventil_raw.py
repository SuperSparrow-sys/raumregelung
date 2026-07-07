"""
Standalone Modbus-RTU Test – Sensoren Adr 1-4 (Reg 0) + Ventil Adr 5 (Reg 4-6)
Keine Projektimporte – nur 'pyserial' wird benötigt.
"""

import serial
import time


def crc16_modbus(data: bytes) -> bytes:
    """Berechnet den Modbus-CRC16 und gibt ihn als 2 Bytes zurück (Low-Byte zuerst)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def sende_befehl(ser: serial.Serial, nutzdaten: bytes) -> bytes:
    """Sendet einen Modbus-Befehl (mit CRC) und gibt die Rohantwort zurück."""
    befehl = nutzdaten + crc16_modbus(nutzdaten)
    ser.reset_input_buffer()
    ser.write(befehl)
    time.sleep(0.2)
    return ser.read(100)


# ── Konfiguration ─────────────────────────────────────────────────────────────
PORT     = '/dev/ttySC0'
BAUDRATE = 38400

ser = serial.Serial(
    port=PORT,
    baudrate=BAUDRATE,
    parity=serial.PARITY_NONE,      # N
    stopbits=serial.STOPBITS_TWO,   # 2
    bytesize=serial.EIGHTBITS,      # 8
    timeout=2
)

print(f"Port: {PORT}  |  {BAUDRATE}-8N2")
print("=" * 50)

# ── Temperatursensoren Adr 1-4, Register 0 (Temperatur, Faktor 0.1, signed) ──
for adresse in [1, 2, 3, 4]:
    nutzdaten = bytes([adresse, 0x03, 0x00, 0x00, 0x00, 0x01])
    antwort = sende_befehl(ser, nutzdaten)
    print(f"Sensor Adr {adresse}:", end="  ")
    if not antwort:
        print("TIMEOUT – keine Antwort")
    elif len(antwort) >= 7:
        rohwert = int.from_bytes(antwort[3:5], byteorder='big', signed=True)
        print(f"{antwort.hex(' ').upper()}  ->  Temperatur: {rohwert / 10:.1f} °C")
    else:
        print(f"Antwort zu kurz ({len(antwort)} Bytes): {antwort.hex(' ').upper()}")

print("=" * 50)

# ── Ventil Adr 5, Register 4-6 ────────────────────────────────────────────────
nutzdaten = bytes([0x05, 0x03, 0x00, 0x04, 0x00, 0x03])
antwort = sende_befehl(ser, nutzdaten)
print("Ventil Adr 5 :", end="  ")
if not antwort:
    print("TIMEOUT – keine Antwort")
elif len(antwort) >= 11:
    reg4 = int.from_bytes(antwort[3:5], byteorder='big')
    reg5 = int.from_bytes(antwort[5:7], byteorder='big')
    reg6 = int.from_bytes(antwort[7:9], byteorder='big')
    print(antwort.hex(' ').upper())
    print(f"  Reg 4 (Rel. Position): {reg4:5d}  ->  {reg4 / 100:.1f} %")
    print(f"  Reg 5               : {reg5:5d}")
    print(f"  Reg 6               : {reg6:5d}")
else:
    print(f"Antwort zu kurz ({len(antwort)} Bytes): {antwort.hex(' ').upper()}")

ser.close()
