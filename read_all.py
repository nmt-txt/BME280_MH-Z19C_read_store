import mh_z19c, bme280

mh = mh_z19c.MH_Z19C(port = "/dev/ttyAMA0")
bme = bme280.BME280(bus=0, cs=0)

print(f" temp: {bme.read_celsius()} celsius degree")
print(f"press: {bme.read_hpa()} hPa")
print(f"humid: {bme.read_rh()} %RH")
print(f"  CO2: {mh.read_ppm()} ppm")

del mh
del bme