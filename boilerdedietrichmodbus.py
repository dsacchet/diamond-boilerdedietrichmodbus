# coding=utf-8

"""
The BoilerDeDietrichModbusCollector class collects metrics from Dedietrich 
boiler using serial modbus

#### Dependencies

 * /dev/ttyUSB0
 * FTDI USB to RS484 adapter
 * pymodbus python library

"""

import diamond.collector
import diamond.convertor
import time
import os
import re

from pymodbus.client.sync import ModbusSerialClient

try:
    import psutil
except ImportError:
    psutil = None


class BoilerDeDietrichModbusCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(BoilerDeDietrichModbusCollector, self).get_default_config_help()
        config_help.update({
            'port': 'Serial port',
            'method': 'Modbus protocol rtu/ascii/binary',
            'baudrate': 'Speed of the serial communcation',
            'bytesize': 'size of unit of the serial communcation',
            'stopbits': 'number of stop bit of the serial communcation',
            'parity': 'parity of the serial communcation even/odd/none',
            'slaveaddr': 'modbus address of the boiler',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(BoilerDeDietrichModbusCollector, self).get_default_config()
        config.update({
            'path':         'boiler',
            'port':         '/dev/ttyUSB0',
            'baudrate':     '9600',
            'bytesize':     '8',
            'stopbits':     '1',
            'parity':       'none',
            'method':       'rtu',
            'slaveaddr':    '0xA',
        })
        return config

    def get_value(self,address,tryout=5):
	client = ModbusSerialClient(method=str(self.config['method']),port=str(self.config['port']),baudrate=int(self.config['baudrate']),bytesize=int(self.config['bytesize']),stopbits=int(self.config['stopbits']),parity=self.parity)
	client.connect()

	# L'interface modbus des chaudieres DeDietrich est un peu speciale
	# car elle fonctionne en bi-maitre. Pendant 5 secondes, elle est
        # maitre et emet des donnees sur le bus modbus, puis elle est escalve
        # pendant 5 secondes, duree pendant laquelle on peut faire nos
	# requetes
	result = None
	while result is None and tryout != 0:
		self.log.error("Boiler / Essai %d"%tryout)
		tryout = tryout-1
		result = client.read_input_registers(address=address, count=1, unit=int(self.config['slaveaddr'],0))
		if result is None and tryout != 0:
			time.sleep(1)

	if tryout != 0:
		value=result.registers[0]
		self.log.error("Boiler / Address %d value : %d" % (address,value) )
		return value
	else:
		self.log.error("Boiler / Unable to get value")
		return None
    

    def collect(self):
        """
        Collect boiler stats.
        """

        # Initialize results
        results = {}

	if self.config['parity'] == "even":
		self.parity='E'
	elif self.config['parity'] == "odd":
		self.parity='O'
	elif self.config['parity'] == "none":
		self.parity='N'
	else:
		self.parity='pas bon'

	##########
	# 7 => outdoor sensor / -500 => 1500 / Increment 1 / Units 0.1 deg C
	outdoor_sensor = self.get_value(7)
	if outdoor_sensor is not None:	
		# Verifie si le bit le plus haut est mis => valeur negative
		if(outdoor_sensor & int('1000000000000000',2) == 32768):
			value=(outdoor_sensor & int('0111111111111111',2))/-10.0
		else:
			value=outdoor_sensor/10.0
		self.publish('outdoor_sensor',value, precision=1)

	##########
	# 18 => room temperature circuit A / 0 => 400 / Increment 1 / Units 0.1 deg C
	room_temp_a = self.get_value(18)
	if room_temp_a is not None:	
		self.publish('room_temp_a',room_temp_a/10.0, precision=1)

	##########
	# 21 => calculated setpoint circuit A / N/A/ / Increment 1 / Units 0.1 deg C
	calc_setpoint_a = self.get_value(21)
	if calc_setpoint_a is not None:	
		self.publish('calc_setpoint_a',calc_setpoint_a/10.0, precision=1)

	##########
	# 62 => dwh temperature / 0 => 1500 / Increment 1 / Units 0.1 deg C
	dhw_temp = self.get_value(62)
	if dhw_temp is not None:	
		self.publish('dhw_temp',dhw_temp/10.0, precision=1)

	##########
        # 74 => boiler calculated setpoint / N/A / Increment 1 / 0.1 deg C
        boiler_calc_setpoint = self.get_value(74)
	if boiler_calc_setpoint is not None:	
		self.publish('boiler_calc_setpoint',boiler_return_temp/10.0, precision=1)

	##########
        # 75 => boiler mit flue temperature / -100 => 1500 / Increment 1 / 0.1 deg C
        boiler_temp = self.get_value(75)
	# Verifie si le bit le plus haut est mis => valeur negative
	if(boiler_temp & int('1000000000000000',2) == 32768):
		value=(boiler_temp & int('0111111111111111',2))/-10.0
	else:
		value=boiler_temp/10.0
	self.publish('boiler_temp',value, precision=1)

	##########
	# 307 => fan speed / 0 => 10000 / Increment 1 / rev/min
	fan_speed = self.get_value(307)
	if fan_speed is not None:	
		self.publish('fan_speed',fan_speed)

	##########
	# 437 => water pressure / 0 => 100 / Increment 1 / 0.1 Bar
	water_pressure = self.get_value(437)
	if water_pressure is not None:	
		self.publish('water_pressure',water_pressure/10.0, precision=1)

	##########
	# 622 => system temperature / 0 => 1500 / Increment 1 / 0.1 deg C
	system_temp = self.get_value(622)
	if system_temp is not None:	
		self.publish('system_temp',system_temp/10.0, precision=1)

	##########
	# 607 => boiler return temperature / 0 => 1500 / Increment 1 / 0.1 deg C
	boiler_return_temp = self.get_value(607)
	if boiler_return_temp is not None:	
		self.publish('boiler_return_temp',boiler_return_temp/10.0, precision=1)

        return None
