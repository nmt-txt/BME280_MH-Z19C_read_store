import spidev

class BME280:
	def __init__(self, bus, cs):
		self.spi = spidev.SpiDev()
		self.spi.open(bus, cs)
		self.spi.mode = 0   # mode0, CPOL=CPHA=0
		self.spi.max_speed_hz = 10 * 10**6 #10MHz

		self._read_trimming_param()

	def __del__(self):
		self.spi.close()

	def _get_reg_addr(self, rw: str, addr: int) -> int:
		rw_flag = 0b1000_0000
		if rw == "w":
			rw_flag = 0b0000_0000

		return rw_flag | (addr & 0b0111_1111)


	def _read_trimming_param(self):
		self.dig = {}
		
		dig_T_raws = self.spi.xfer2([self._get_reg_addr("r", 0x88)] + [0]* 6)
		b_p = 1
		for i, f in zip(range(3), [False] + [True]*2, strict=True):
			i_ = i+1
			self.dig[f"T{i_}"] = int.from_bytes(dig_T_raws[b_p:b_p+2], "little", signed = f)
			b_p += 2

		dig_P_raws = self.spi.xfer2([self._get_reg_addr("r", 0x8E)] + [0]*18)
		b_p = 1
		for i, f in zip(range(9), [False] + [True]*8, strict=True):
			i_ = i+1
			self.dig[f"P{i_}"] = int.from_bytes(dig_P_raws[b_p:b_p+2], "little", signed = f)
			b_p += 2

		dig_H_raws = [self.spi.xfer2([self._get_reg_addr("r", 0xA1), 0])[1]] + \
				self.spi.xfer2([self._get_reg_addr("r", 0xE1)] + [0]*8)[1:9]
		self.dig["H1"] = int.from_bytes(dig_H_raws[0:1],   "little", signed = False)
		self.dig["H2"] = int.from_bytes(dig_H_raws[1:3],   "little", signed = True)
		self.dig["H3"] = int.from_bytes(dig_H_raws[3:4],   "little", signed = False)
		self.dig["H4"] = dig_H_raws[4] << 4 | (dig_H_raws[5] & 0b00001111)
		self.dig["H5"] = dig_H_raws[6] << 4 | ((dig_H_raws[5]>>4) & 0b00001111)
		self.dig["H6"] = int.from_bytes(dig_H_raws[7:8],   "little", signed = True)


	def _get_calibrated_celsius(self, temp_raw) -> float:
		var1 = (((temp_raw>>3) - (self.dig["T1"]<<1)) * self.dig["T2"]) >> 11
		var2 = (((((temp_raw>>4) - self.dig["T1"]) * ((temp_raw>>4) - self.dig["T1"])) >> 12) * self.dig["T3"]) >> 14
		self.t_fine = var1 + var2

		temp = (self.t_fine * 5 + 128) >> 8
		return temp/100

	def _get_calibrated_hpa(self, press_raw) -> float:
		var1 = self.t_fine - 128000
		var2 = var1**2 * self.dig["P6"]
		var2 = var2 + ((var1*self.dig["P5"])<<17)
		var2 = var2 + (self.dig["P4"] <<35)
		var1 = ((var1**2 * self.dig["P3"])>>8) + ((var1 * self.dig["P2"])<<12)
		var1 = ((((1<<47)+var1)) * (self.dig["P1"]))>>33
		if var1==0:
			return 0.
		p = 1048576 - press_raw
		p = (((p<<31)-var2)*3125)//var1
		var1 = ((self.dig["P9"]) * (p>>13) * (p>>13)) >> 25
		var2 = ((self.dig["P8"]) * p) >> 19
		p = ((p + var1 + var2) >> 8) + (self.dig["P7"] << 4)
		return p/256/100

	def _get_calibrated_rh(self, humid_raw) -> float:
		v_x1_u32r = (self.t_fine - 76800)
		v_x1_u32r = (
			(	(((humid_raw << 14) - ((self.dig["H4"]) << 20) - ((self.dig["H5"]) * v_x1_u32r)) +
				(16384)) >> 15

			) *
			(((
				(	(((v_x1_u32r * (self.dig["H6"])) >> 10) * (((v_x1_u32r *
					(self.dig["H3"])) >> 11) + (32768))) >> 10

				) + 
			(2097152)) * (self.dig["H2"]) + 8192) >> 14)
		)
		v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * (self.dig["H1"])) >> 4))
		v_x1_u32r = 0 if v_x1_u32r < 0 else v_x1_u32r
		v_x1_u32r = 419430400 if v_x1_u32r > 419430400 else v_x1_u32r
		return (v_x1_u32r >> 12) / 1024



	def read_celsius(self):
		temp_raw_bins = self.spi.xfer2([self._get_reg_addr("r", 0xFA), 0, 0, 0])
		temp_raw = (temp_raw_bins[1] << 8+4) | (temp_raw_bins[2] << 4) | ((temp_raw_bins[3]>>4) & 0b00001111)
		return self._get_calibrated_celsius(temp_raw)

	def update_t_fine(self):
		self.read_celsius()

	def read_hpa(self):
		self.update_t_fine()

		press_raw_bins = self.spi.xfer2([self._get_reg_addr("r", 0xF7), 0, 0, 0])
		press_raw = (press_raw_bins[1]<<8+4) + (press_raw_bins[2]<<4) + ((press_raw_bins[3]>>4)&0b00001111)
		return self._get_calibrated_hpa(press_raw)

	def read_rh(self):
		self.update_t_fine()

		humid_raw_bins = self.spi.xfer2([self._get_reg_addr("r", 0xFD), 0,0])[1:3]
		humid_raw = (humid_raw_bins[0] << 8) | humid_raw_bins[1]
		return self._get_calibrated_rh(humid_raw)

	def _write(self, addr, contents):
		self.spi.xfer2([self._get_reg_addr("w", addr)] + contents)
	
	def _read(self, addr, size):
		r = self.spi.xfer2([self._get_reg_addr("r", addr)] + [0]*size)[1:size+1]
		return r

	# not used right now
	def write_ctrl_meas(
		self, 
		temp_oversampling_num = -1, 
		press_oversampling_num = -1,
		mode=""
	):
		ctrl_meas_old = self.spi.xfer2([self.get_reg_addr("r", 0xF4), 0])[1]

		val_temp = {
			-1:ctrl_meas_old & 0b1110_0000,
			0: 0b000_000_00,
			1: 0b001_000_00,
			2: 0b010_000_00,
			4: 0b011_000_00,
			8: 0b100_000_00,
			16:0b101_000_00
		}

		val_press = {
			-1:ctrl_meas_old & 0b0001_1100,
			0: 0b000_000_00,
			1: 0b000_001_00,
			2: 0b000_010_00,
			4: 0b000_011_00,
			8: 0b000_100_00,
			16:0b000_101_00
		}

		val_mode = {
			"": ctrl_meas_old & 0b0000_0011,
			"sleep": 0b000_000_00,
			"forced": 0b000_000_01,
			"normal": 0b000_000_11
		}

		if temp_oversampling_num not in val_temp:
			raise ValueError("temp_oversampling_num must be 0, 1, 2, 4, 8, or 16")
		if press_oversampling_num not in val_press:
			raise ValueError("press_oversampling_num must be 0, 1, 2, 4, 8, or 16")
		if mode not in val_mode:
			raise ValueError("mode must be sleep, forced, or normal")

		self.spi.xfer2([
			self.get_reg_addr("w", 0xF4), 
			val_temp[temp_oversampling_num] | val_press[press_oversampling_num] | val_mode[mode]
		])


		def vind(v, d):
			keys = [k for k, v_ in d.items() if v_ == v]
			if keys:
				return keys[0]
			raise ValueError()

		ctrl_meas_raw = self.spi.xfer2([self.get_reg_addr("r", 0xF4), 0])[1]
		ctrl_meas = []
		ctrl_meas.append(vind(ctrl_meas_raw & 0b111_000_00, val_temp))
		ctrl_meas.append(vind(ctrl_meas_raw & 0b000_111_00, val_press))
		ctrl_meas.append(vind(ctrl_meas_raw & 0b000_000_11, val_mode))
		return ctrl_meas

if __name__ == "__main__":
	bme = BME280(bus = 0, cs = 0)
	print(f"{bme.read_celsius()} celsius degree")
	print(f"{bme.read_hpa()} hPa")
	print(f"{bme.read_rh()} %RH")

	del bme