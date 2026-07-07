"""
Standalone Modbus-RTU Test – Slave 5, Register 4 / 5 / 6
Keine Projektimporte – nur 'pyserial' wird benötigt.

Befehlsaufbau (FC 03, 3 Register ab Adresse 4):
    05 03 00 04 00 03 <CRC-Lo> <CRC-Hi>
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


# ── Konfiguration ─────────────────────────────────────────────────────────────
PORT     = '/dev/serial0'   # ggf. auf /dev/ttyAMA10 ändern
BAUDRATE = 38400

ser = serial.Serial(
    port=PORT,
    baudrate=BAUDRATE,
    parity=serial.PARITY_NONE,      # N
    stopbits=serial.STOPBITS_TWO,   # 2
    bytesize=serial.EIGHTBITS,      # 8
    timeout=2
)

# ── Befehl aufbauen ───────────────────────────────────────────────────────────
# Slave 5 | FC 03 | Start-Register 4 | Anzahl 3 Register
nutzdaten = bytes([0x05, 0x03, 0x00, 0x04, 0x00, 0x03])
befehl    = nutzdaten + crc16_modbus(nutzdaten)

print(f"Port  : {PORT}  |  {BAUDRATE}-8N2")
print(f"Befehl: {befehl.hex(' ').upper()}")
print("Sende Anfrage an Slave 5 ...")

ser.write(befehl)
time.sleep(0.2)

antwort = ser.read(100)
ser.close()

# ── Auswertung ────────────────────────────────────────────────────────────────
if not antwort:
    print("\nFEHLER: Timeout – Slave 5 antwortet nicht.")
else:
    print(f"\nANTWORT ({len(antwort)} Bytes): {antwort.hex(' ').upper()}")

    # Erwartete Antwort bei 3 Registern:
    # Addr(1) + FC(1) + ByteCount(1) + 6 Datenbytes + CRC(2) = 11 Bytes
    if len(antwort) >= 11:
        reg4 = int.from_bytes(antwort[3:5], byteorder='big')
        reg5 = int.from_bytes(antwort[5:7], byteorder='big')
        reg6 = int.from_bytes(antwort[7:9], byteorder='big')

        print(f"\nRegister 4 (Rel. Position): {reg4:5d}  ->  {reg4 / 100:.1f} %")
        print(f"Register 5               : {reg5:5d}")
        print(f"Register 6               : {reg6:5d}")
    else:
        print(f"Warnung: Antwort zu kurz ({len(antwort)} Bytes, erwartet >= 11).")
