import mariadb
import sys
import mh_z19c, bme280

try:
	conn = mariadb.connect(
		user     = ,# ユーザ名
		password = ,# パスワード
		host     = "127.0.0.1",
		port     = 3306,
		database = ,# データベース名
		autocommit=True
	)
except mariadb.Error as e:
	print(f"db connect error: {e}")
	sys.exit(-1)

mh = mh_z19c.MH_Z19C(port="/dev/ttyAMA0")
bme = bme280.BME280(bus=0, cs=0)

temp  = bme.read_celsius()
humid = bme.read_rh()
press = bme.read_hpa()
co2   =  mh.read_ppm()

sql = 'INSERT INTO sensor (datetime, temp, humid, press, co2) VALUES(NOW(), ?, ?, ?, ?)'

cur = conn.cursor()
try:
	cur.execute(sql, (temp, humid, press, co2))
except Exception as e:
	print(f"insert error: {e}")
finally:
	cur.close()

conn.close()
del mh
del bme