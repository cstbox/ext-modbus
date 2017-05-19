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
import struct
import logging

from pycstbox.log import Loggable
from pycstbox.hal import HalError
from pycstbox.hal.device import PolledDevice, CommunicationError, CRCError
from pycstbox.minimalmodbus import register_serial_port, Instrument, BAUDRATE, PARITY, BYTESIZE, STOPBITS, TIMEOUT

_logger = logging.getLogger('modbus')


class RTUModbusHALDevice(PolledDevice):
    """ RTU devices share the serial port on which the RS485 line is connected. """
    def __init__(self, coord_cfg, dev_cfg):
        # create the shared serial port in minimalmodbus dictionary if not yet known
        port_cfg = dict(
            baudrate=getattr(coord_cfg, 'baudrate', BAUDRATE),
            parity=getattr(coord_cfg, 'parity', PARITY),
            bytesize=getattr(coord_cfg, 'bytesize', BYTESIZE),
            stopbits=getattr(coord_cfg, 'stopbits', STOPBITS),
            timeout=getattr(coord_cfg, 'timeout', TIMEOUT)
        )
        register_serial_port(coord_cfg.port, logger=_logger, **port_cfg)

        super(RTUModbusHALDevice, self).__init__(coord_cfg, dev_cfg)

    def poll(self):
        try:
            return super(RTUModbusHALDevice, self).poll()
        except ValueError as e:
            # minimalmodbus based HW devices report CRC errors as ValueError
            raise CRCError(self.device_id, e)


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


class RTUModbusHWDevice(Instrument, Loggable):
    """ Base class for implementing Modbus equipments deriving from minimalmodbus.Instrument.

    It takes care among other of communication errors recovery in a uniform way.
    """
    DEFAULT_RETRIES = 3
    STATS_INTERVAL = 1000

    def __init__(self, port, unit_id, logname, retries=DEFAULT_RETRIES):
        """
        :param str port: serial port on which the RS485 interface is connected
        :param int unit_id: the address of the device
        :param str logname: the (short) root for the name of the log
        :param int retries: number of retries in case of communication errors
        """
        super(RTUModbusHWDevice, self).__init__(port=port, slaveaddress=int(unit_id))

        self._first_poll = True
        self.poll_req_interval = 0
        self.retries = retries
        self.terminate = False
        self.communication_error = False

        self.total_reads = 0
        self.total_errors = 0

        Loggable.__init__(self, logname='%s-%03d' % (logname, self.unit_id))

        self.log_info('created %s instance with unit id=%d on port %s', self.__class__.__name__, unit_id, port)

    @property
    def unit_id(self):
        """ The id of the device """
        return self.address

    def _read_registers(self, start_addr=0, reg_count=1):
        """ Read a bunch of registers and return the resulting raw data buffer

        :param int start_addr: the address of the first register (default: 0)
        :param int reg_count: the number of 16 bits registers to read (default: 1)
        :return: the registers content as a string, or None if a communication error occurred
        :rtype: str
        """
        if self.serial.isOpen():
            # ensure no junk is lurking there
            self.serial.flushInput()
            self.serial.flushOutput()

        try:
            data = self.read_string(start_addr, reg_count)
        except IOError as e:
            raise CommunicationError(self.unit_id, e)
        except ValueError as e:
            raise CRCError(self.unit_id, e)
        else:
            return data

    def reset(self):
        self.log_warning('resetting communications and device')
        self.reset_communications()
        self.reset_device()

    def reset_communications(self):
        self.serial.close()
        time.sleep(self.poll_req_interval)
        self.serial.open()
        time.sleep(0.1)
        self.serial.flushInput()
        self.serial.flushOutput()

    def reset_device(self):
        pass

    def unpack_registers(self, start_register, reg_count=1, unpack_format='>h'):
        """ Reads and unpacks registers. 
        
        :param ModbusRegister start_register: the register to start the read from
        :param int reg_count: see :py:meth:`_read_registers`
        :param str unpack_format: unpack format as used by :py:meth:`struct.unpack`
        :return: the register(s) content as a tuple
        :rtype: tuple
        :raise HalError: in case of read error
        """
        start_addr = start_register.addr
        data = self._read_registers(start_addr, reg_count)
        if data is None:
            raise HalError('read register failed (start=%d count=%d)' % (start_addr, reg_count))
        return struct.unpack_from(unpack_format, data)
