import spidev
import sys

def get_reg_addr(rw: str, addr: int) -> int:
	rw_flag = 0b1000_0000
	if rw == "w":
		rw_flag = 0b0000_0000

	return rw_flag | (addr & 0b0111_1111)

spi = spidev.SpiDev()
spi.open(0, 0) # bus0, cs0
spi.mode = 0   # mode0, CPOL=CPHA=0
spi.max_speed_hz = 10 * 10**6 #10MHz

bme_id = spi.xfer2([get_reg_addr("r", 0xD0), 0])[1]

if bme_id != 0x60:
	print(f"ID not match! actual:{bme_id}, expect: 0x60" ,file=sys.stderr)
	spi.close()
	sys.exit(-1)

# humid oversampling x1
r = spi.xfer2([get_reg_addr("r", 0xF2), 0])[1]
ctrl_hum = r & 0b1111_1000 | 0b001
spi.xfer2([get_reg_addr("w", 0xF2), ctrl_hum])

# press, temp oversampling x1, normal mode
ctrl_meas = (0b001 << 5) + (0b001 << 3) + 0b11
spi.xfer2([get_reg_addr("w", 0xF4), ctrl_meas])

# standby 1000ms, filter off, disable 3-wire SPI
config = (0b101 << 5) | (0b000 << 3) | 0b00
spi.xfer2([get_reg_addr("w",0xF5), config])

spi.close()