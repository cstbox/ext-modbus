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
