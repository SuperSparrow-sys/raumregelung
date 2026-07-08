"""
Standalone Bus-Test – exakte Werte aus dem funktionierenden Skript:
  Port     : /dev/ttySC1
  Protokoll: 38400, 8E1 (Even-Parität, 1 Stopbit)
  RS485    : RTS-Richtungssteuerung aktiv
  Sensoren : Adr 1-4, FC03, Reg 0, Faktor 0.1 -> °C
  Ventil   : Adr 5,   FC03, Reg 4, Faktor 0.01 -> %
Keine Projektimporte – nur 'minimalmodbus' und 'pyserial'.
"""

import minimalmodbus
import serial
from serial.rs485 import RS485Settings
import time

# ── Konfiguration ──────────────────────────────────────────────────────────────
PORT            = '/dev/ttySC1'
BAUDRATE        = 38400
VENTIL_ADR      = 5
SENSOR_ADRESSEN = [1, 2, 3, 4]

# ── Schnittstelle einmalig öffnen (8E1 + RS485-RTS) ───────────────────────────
base = minimalmodbus.Instrument(PORT, slaveaddress=1)
base.serial.baudrate = BAUDRATE
base.serial.bytesize = 8
base.serial.parity   = serial.PARITY_EVEN
base.serial.stopbits = 1
base.serial.timeout  = 0.2
base.mode            = minimalmodbus.MODE_RTU
base.serial.rs485_mode = RS485Settings(
    rts_level_for_tx=True,
    rts_level_for_rx=False,
    delay_before_tx=0.0,
    delay_before_rx=0.0,
)

# Alle Geräte teilen sich denselben geöffneten Port
sensoren = {}
for adr in SENSOR_ADRESSEN:
    instr = minimalmodbus.Instrument(PORT, slaveaddress=adr)
    instr.serial = base.serial
    instr.mode   = minimalmodbus.MODE_RTU
    sensoren[adr] = instr

ventil = minimalmodbus.Instrument(PORT, slaveaddress=VENTIL_ADR)
ventil.serial = base.serial
ventil.mode   = minimalmodbus.MODE_RTU

# ── Einmaliger Test ────────────────────────────────────────────────────────────
print(f"Port: {PORT}  |  {BAUDRATE}-8E1  (RS485-RTS aktiv)")
print("=" * 55)

# Sensoren 1-4: Reg 0, Faktor 0.1, signed
for adr, sensor in sensoren.items():
    try:
        temp = sensor.read_register(0, number_of_decimals=1, functioncode=3)
        print(f"Sensor Adr {adr}: {temp:.1f} °C")
    except Exception as e:
        print(f"Sensor Adr {adr}: FEHLER – {e}")
    time.sleep(0.05)

print("-" * 55)

# Ventil Adr 5: Reg 4 lesen, Faktor 0.01 -> %
try:
    pos = ventil.read_register(4, number_of_decimals=2, functioncode=3)
    print(f"Ventil Adr {VENTIL_ADR}: Ist-Position (Reg 4) = {pos:.1f} %")
except Exception as e:
    print(f"Ventil Adr {VENTIL_ADR}: LESEFEHLER Reg 4 – {e}")

print("=" * 55)
base.serial.close()
