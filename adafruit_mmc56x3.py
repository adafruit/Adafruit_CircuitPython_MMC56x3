# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_mmc56x3`
================================================================================

Python MMC5603 / MMC5613 magnetometer sensor library


* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* `Adafruit MMC5603 Magnetometer <https://www.adafruit.com/product/5579>`

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import time
from micropython import const
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct, Struct
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_bit import RWBit

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MMC56x3.git"

_MMC5603_I2CADDR_DEFAULT: int = const(0x30)  # Default I2C address
_MMC5603_CHIP_ID = const(0x10)

_MMC5603_OUT_X_L = const(0x00)  # Register that starts the mag data out
_MMC5603_OUT_TEMP = const(0x09)  # Register that contains temp reading
_MMC5603_PRODUCT_ID = const(0x39)  # Register that contains the part ID
_MMC5603_STATUS_REG = const(0x18)  # Register address for device status
_MMC5603_CTRL_REG0 = const(0x1B)  # Register address for control 0
_MMC5603_CTRL_REG1 = const(0x1C)  # Register address for control 1
_MMC5603_CTRL_REG2 = const(0x1D)  # Register address for control 2

class MMC5603:
    """Driver for the MMC5603 3-axis magnetometer.
    :param ~busio.I2C i2c_bus: The I2C bus the MMC5603 is connected to.
    :param address: The I2C device address. Defaults to :const:`0x30`
    **Quickstart: Importing and using the device**
        Here is an example of using the :class:`MMC5603` class.
        First you will need to import the libraries to use the sensor
        .. code-block:: python
            import board
            import adafruit_mmc56x3
        Once this is done you can define your `board.I2C` object and define your sensor object
        .. code-block:: python
            i2c = board.I2C()
            sensor = adafruit_mmc56x3.MMC5603(i2c)
        Now you have access to the :attr:`magnetic` attribute
        .. code-block:: python
            mag_x, mag_y, mag_z = sensor.magnetic
    """

    _chip_id = ROUnaryStruct(_MMC5603_PRODUCT_ID, "<B")
    _ctrl0_reg = UnaryStruct(_MMC5603_CTRL_REG0, "<B")
    _ctrl1_reg = UnaryStruct(_MMC5603_CTRL_REG1, "<B")
    _status_reg = ROUnaryStruct(_MMC5603_STATUS_REG, "<B")

    _reset = RWBit(_MMC5603_CTRL_REG1, 7)
    _meas_m_done = RWBit(_MMC5603_STATUS_REG, 6)
    _meas_t_done = RWBit(_MMC5603_STATUS_REG, 7)

    _raw_temp_data = ROUnaryStruct(_MMC5603_OUT_TEMP, "<B")

    """
    _perf_mode = RWBits(2, _LIS3MDL_CTRL_REG1, 5)
    _z_perf_mode = RWBits(2, _LIS3MDL_CTRL_REG4, 2)
    _operation_mode = RWBits(2, _LIS3MDL_CTRL_REG3, 0)
    _data_rate = RWBits(4, _LIS3MDL_CTRL_REG1, 1)
    """

    def __init__(self, i2c_bus, address=_MMC5603_I2CADDR_DEFAULT):
        # pylint: disable=no-member
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        if self._chip_id != _MMC5603_CHIP_ID:
            raise RuntimeError("Failed to find MMC5603 - check your wiring!")

        self.reset()
        self._buffer = bytearray(9)
        #self.performance_mode = PerformanceMode.MODE_ULTRA

        #self.data_rate = Rate.RATE_155_HZ
        #self.range = Range.RANGE_4_GAUSS
        #self.operation_mode = OperationMode.CONTINUOUS



    def reset(self):  # pylint: disable=no-self-use
        """Reset the sensor to the default state set by the library"""
        self._ctrl1_reg = 0x80  # write only, set topmost bit
        time.sleep(0.020)

    @property
    def temperature(self):
        """The processed temperature sensor value, returned in floating point C
        """
        self._ctrl0_reg = 0x02  # TM_T + Auto_SR_en
        while not self._meas_t_done:
            time.sleep(0.005)
        t = self._raw_temp_data
        t *= 0.8  # 0.8*C / LSB
        t -= 75   # 0 value is -75
        return t


    @property
    def magnetic(self):
        """The processed magnetometer sensor values.
        A 3-tuple of X, Y, Z axis values in microteslas that are signed floats.
        """
        self._ctrl0_reg = 0x21  # TM_M + Auto_SR_en
        while not self._meas_m_done:
            time.sleep(0.005)
        self._buffer[0] = _MMC5603_OUT_X_L
        with self.i2c_device as i2c:
            i2c.write_then_readinto(self._buffer, self._buffer,
                                    out_end=1)
        x = (self._buffer[0] << 12 | self._buffer[1] << 4 | self._buffer[6] >> 4)
        y = (self._buffer[2] << 12 | self._buffer[3] << 4 | self._buffer[7] >> 4)
        z = (self._buffer[4] << 12 | self._buffer[5] << 4 | self._buffer[8] >> 4)
        # fix center offsets
        x -=  1<<19
        y -=  1<<19
        z -=  1<<19
        # scale to uT by LSB in datasheet
        x *= 0.00625
        y *= 0.00625
        z *= 0.00625
        return (x, y, z)

    @property
    def data_rate(self):
        """The rate at which the sensor takes measurements. Must be a ``Rate``"""
        return self._data_rate

    @data_rate.setter
    def data_rate(self, value):
        # pylint: disable=no-member
        if value is Rate.RATE_155_HZ:
            self.performance_mode = PerformanceMode.MODE_ULTRA
        if value is Rate.RATE_300_HZ:
            self.performance_mode = PerformanceMode.MODE_HIGH
        if value is Rate.RATE_560_HZ:
            self.performance_mode = PerformanceMode.MODE_MEDIUM
        if value is Rate.RATE_1000_HZ:
            self.performance_mode = PerformanceMode.MODE_LOW_POWER
        sleep(0.010)
        if not Rate.is_valid(value):
            raise AttributeError("`data_rate` must be a `Rate`")
        self._data_rate = value

    @property
    def performance_mode(self):
        """Sets the 'performance mode' of the sensor. Must be a ``PerformanceMode``.
        Note that `performance_mode` affects the available data rate and will be
        automatically changed by setting ``data_rate`` to certain values."""

        return self._perf_mode

    @performance_mode.setter
    def performance_mode(self, value):
        if not PerformanceMode.is_valid(value):
            raise AttributeError("`performance_mode` must be a `PerformanceMode`")
        self._perf_mode = value
        self._z_perf_mode = value

    @property
    def operation_mode(self):
        """The operating mode for the sensor, controlling how measurements are taken.
        Must be an `OperationMode`. See the the `OperationMode` document for additional details
        """
        return self._operation_mode

    @operation_mode.setter
    def operation_mode(self, value):
        if not OperationMode.is_valid(value):
            raise AttributeError("operation mode must be a OperationMode")
        self._operation_mode = value
