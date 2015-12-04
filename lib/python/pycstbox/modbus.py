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


class ModbusRegister(namedtuple('ModbusRegister', ['addr', 'size', 'cfgreg', 'decoder', 'encoder'])):
    """ Modbus register description.

    :var addr: register address
    :var int size: register size (in 16 bits words)
    :var bool cfgreg: True if this register is a configuration one
    :var decoder: a function which takes to register value and returns the corresponding real one
    :var encoder: a function which takes a real value and returns the corresponding register one
    """
    @staticmethod
    def identity(value):
        return value

    def __new__(cls, addr, size=1, cfgreg=False, decoder=identity, encoder=identity):
        """ Overridden __new__ allowing default values for tuple attributes. """
        return super(ModbusRegister, cls).__new__(addr, size, cfgreg, encoder, decoder)
