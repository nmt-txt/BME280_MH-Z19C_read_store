import serial
import time

class MH_Z19C:
	def __init__(self, port, timeout=5.0, write_timeout=5.0):
		self.serial = serial.Serial(
			port          = port,
			baudrate      = 9600,
			bytesize      = serial.EIGHTBITS,
			parity        = serial.PARITY_NONE,
			stopbits      = serial.STOPBITS_ONE,
			timeout       = timeout,
			write_timeout = write_timeout
		)

		self.serial.reset_input_buffer()
		self.serial.reset_output_buffer()
	
	def __del__(self):
		self.serial.close()

	def _is_collect_checksum(self, r) -> bool:		
		for_check=0
		
		for i, b in enumerate(r):
			if i==0 or i==8:
				continue
			# チェックサムは1バイト、溢れた分は捨てる
			for_check = for_check + b & 0b1111_1111

		for_check = 0xFF - for_check + 1

		return r[8] == for_check

	def read_ppm(self):
		RETRY_MAX = 5
		retry_num = 0

		while retry_num < RETRY_MAX:
			s = bytearray.fromhex("FF 01 86 00 00 00 00 00 79")
			self.serial.write(s)
			r = self.serial.read(size=9)

			if self._is_collect_checksum(r):
				r = r[2] * 256 + r[3]
				break
			
			retry_num+=1
			time.sleep(5)
		else:
			r = 0
		return r

if __name__ == "__main__":
	PORT = "/dev/ttyAMA0"

	mh = MH_Z19C(PORT)
	print(f"{mh.read_ppm()} ppm")

	del mh