#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of CSTBox.
#
# CSTBox is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CSTBox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with CSTBox.  If not, see <http://www.gnu.org/licenses/>.

""" Common definitions and helpers for Modbus devices support."""

from collections import namedtuple
import time

import minimalmodbus

from pycstbox.log import Loggable


class ModbusRegister(namedtuple('ModbusRegister', ['addr', 'size', 'cfgreg', 'signed'])):
    """ Modbus register description.

    :var addr: register address
    :var int size: register size (in 16 bits words)
    :var bool cfgreg: True if this register is a configuration one (default: False)
    :var bool signed: True if the value is signed (default: False)
    """
    __slots__ = ()

    def __new__(cls, addr, size=1, cfgreg=False, signed=False):
        """ Overridden __new__ allowing default values for tuple attributes. """
        return super(ModbusRegister, cls).__new__(cls, addr, size, cfgreg, signed)

    @staticmethod
    def decode(raw):
        """ Default decoding (identity)

        :param raw: the register raw content
        :return: the converted value
        :rtype: int
        """
        return raw

    @property
    def unpack_format(self):
        fmt = 'H' if self.size == 1 else 'I'
        if self.signed:
            return fmt.lower()
        else:
            return fmt


class RTUModbusHWDevice(minimalmodbus.Instrument, Loggable):
    """ Base class for implementing Modbus equipements deriving from minimalmodbus.Instrument.

    It takes care among other of communication errors recovery in a uniform way.
    """
    DEFAULT_BAUDRATE = 9600
    DEFAULT_TIMEOUT = 2
    DEFAULT_RETRIES = 3
    STATS_INTERVAL = 100

    def __init__(self, port, unit_id, logname, baudrate=DEFAULT_BAUDRATE, retries=DEFAULT_RETRIES):
        """
        :param str port: serial port on which the RS485 interface is connected
        :param int unit_id: the address of the device
        :param str logname: the (short) root for the name of the log
        :param int baudrate: the serial communication baudrate
        """
        super(RTUModbusHWDevice, self).__init__(port=port, slaveaddress=int(unit_id))

        self.serial.close()
        self.serial.setBaudrate(baudrate)
        self.serial.setTimeout(self.DEFAULT_TIMEOUT)
        self.serial.open()

        # wait a bit to ensure we call clean it correctly (spurious data present
        # sometimes when opening serial on RasPi)
        time.sleep(0.1)
        self.serial.flushInput()
        self.serial.flushOutput()

        self._first_poll = True
        self.poll_req_interval = 0
        self.retries = retries
        self.terminate = False
        self.communication_error = False

        self.total_requests = 0
        self.total_reads = 0
        self.total_errors = 0

        Loggable.__init__(self, logname='%s-%03d' % (logname, self.unit_id))

        self.log_info(
            'created %s instance with configuration %s',
            self.__class__.__name__,
                {
                    "port": port,
                    "unit_id": unit_id,
                    "baudrate": baudrate
                }
        )

    @property
    def unit_id(self):
        """ The id of the device """
        return self.address

    def _read_registers(self, start_addr=0, reg_count=1):
        """ Read a bunch of registers and return the resulting raw data buffer

        :param int start_addr: the address of the first register (default: 0)
        :param int reg_count: the number of 16 bits registers to read (default: 1)
        :return: the registers content as a string, or None if a communication error occurred
        """
        if self.total_requests and self.total_requests % self.STATS_INTERVAL == 0:
            self.log_info(
                    'traffic stats: totreqs=%d totreads=%d toterrs=%d',
                    self.total_requests, self.total_reads, self.total_errors
            )

        self.total_requests += 1

        if self.serial.isOpen():
            # ensure no junk is lurking there
            self.serial.flushInput()
            self.serial.flushOutput()

        attempts_left = self.retries
        while True:
            try:
                self.total_reads += 1
                data = self.read_string(start_addr, reg_count)

            except ValueError:
                self.total_errors += 1

                # CRC error is reported as ValueError
                attempts_left -= 1

                # reset the serial link, wait a bit and retry until max attempts
                if attempts_left:
                    self.log_warning('trying to recover from error (attempts remaining=%d)', attempts_left)
                    self.serial.close()
                    time.sleep(self.poll_req_interval)
                    self.serial.open()
                    time.sleep(0.1)
                    self.serial.flushInput()
                    self.serial.flushOutput()

                else:
                    self.log_error('cannot recover from error, request ignored')
                    self.communication_error = True

                    return None

            else:
                if self.communication_error:
                    self.log_info('recovered from error')
                    self.communication_error = False
                return data
