# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

""" Display magnetometer data once per second """

import time
import board
import adafruit_mmc56x3

i2c = board.I2C()  # uses board.SCL and board.SDA

from adafruit_debug_i2c import DebugI2C
debug_i2c = DebugI2C(i2c)
sensor = adafruit_mmc56x3.MMC5603(debug_i2c)

while True:
    mag_x, mag_y, mag_z = sensor.magnetic
    temp = sensor.temperature
    
    print("X:{0:10.2f}, Y:{1:10.2f}, Z:{2:10.2f} uT  Temp:{3:10.1f}*C".format(mag_x, mag_y, mag_z, temp))
    print("")
    time.sleep(1.0)
