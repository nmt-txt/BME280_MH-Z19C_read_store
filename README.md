# BME280_MH-Z19C_read_store

## 概要

Raspberry Piに接続されたBME280とMH-Z19Cから、気温・湿度・気圧・CO2濃度を読み取ります(MariaDBへ保存します)。

## 必要環境

- pyserial
- spidev

```console
$ pip3 install spidev
$ pip3 install pyserial
```

Raspberry PiのSPIとシリアル通信を有効にしていること

```console
$ sudo raspi-config
```

## 使い方

BMI280はSPIの0番バス・チップセレクト0番に、MH-Z19Cは`/dev/ttyAMA0`に接続されている前提です。
各環境に合わせて書き換えてください。

- bme280_init.py
  - BME280の気温・湿度・気圧オーバーサンプリングを1回、ノーマルモード、standby1000msにセットする
- bme280.py
  - BME280から値を読み取り補正等を行うクラス
- mh_z19c.py
  - MH-Z19Cから値を読み取るクラス
- read_all.py
  - 2つのセンサから値を読み取り表示する
- read_save_db.py
  - 2つのセンサから値を読み取り、データベースへ保存する
  - 先にユーザ名、パスワード、データベース名を記述する必要があります
  - 想定しているDBスキーム: `mysql> create table sensor (datetime datetime not null primary key, temp double, humid double, press double, co2 double);`
