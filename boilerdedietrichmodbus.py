# coding=utf-8

"""
The BoilerDeDietrichModbusCollector class collects metrics from Dedietrich 
boiler using serial modbus

#### Dependencies

 * /dev/ttyUSB0
 * FTDI USB to RS484 adapter
 * minimalmodbus python library

"""

import diamond.collector
import diamond.convertor
import time
import os
import re
import minimalmodbus

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
            'timeout': 'modbus read/write timeout',
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
            'timeout':      '1',
        })
        return config

    def get_value(self,instrument,address,numberOfDecimals=0,signed=False,functioncode=3,tryout=40):

	while tryout != 0:
		try:
			value = instrument.read_register(address,numberOfDecimals,functioncode,signed)
		except (IOError, ValueError, TypeError):
			tryout=tryout-1
		else:
			self.log.debug("Boiler / Address %d value : %0.2f" % (address,value) )
			return value

	self.log.error("Boiler / Unable to get value %d" % address)
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

	instrument = minimalmodbus.Instrument(str(self.config['port']),int(self.config['slaveaddr'],0),mode=str(self.config['method']))

	instrument.serial.baudrate = int(self.config['baudrate'])
	instrument.serial.bytesize = int(self.config['bytesize'])
	instrument.serial.parity = self.parity
	instrument.serial.stopbits = int(self.config['stopbits'])
	instrument.serial.timeout = float(self.config['timeout'])

	minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL=True

	##########
	# 7 => outdoor sensor / -500 => 1500 / Increment 1 / Units 0.1 deg C
	outdoor_sensor = self.get_value(instrument,7,0,False)
	if outdoor_sensor is not None:	
		# Verifie si le bit le plus haut est mis => valeur negative
		if(int(outdoor_sensor) & int('1000000000000000',2) == 32768):
			value=(int(outdoor_sensor) & int('0111111111111111',2))/-10.0
		else:
			value=outdoor_sensor/10.0
		self.publish('outdoor_sensor',value, precision=1)

	##########
	# 14 => temperature jour set day circuit A / 0 => 400 / Increment 1 / Units 0.1 deg C
	room_temp_day_a = self.get_value(instrument,14,1,False)
	if room_temp_day_a is not None:	
		self.publish('room_temp_a',room_temp_day_a, precision=1)

	##########
	# 15 => room temperature set night circuit A / 0 => 400 / Increment 1 / Units 0.1 deg C
	room_temp_night_a = self.get_value(instrument,15,1,False)
	if room_temp_night_a is not None:	
		self.publish('room_temp_a',room_temp_night_a, precision=1)

	##########
	# 16 => room temperature set antifrost circuit A / 0 => 400 / Increment 1 / Units 0.1 deg C
	room_temp_antifrost_a = self.get_value(instrument,16,1,False)
	if room_temp_antifrost_a is not None:	
		self.publish('room_temp_a',room_temp_antifrost_a, precision=1)

	##########
	# 18 => room temperature circuit A / 0 => 400 / Increment 1 / Units 0.1 deg C
	room_temp_a = self.get_value(instrument,18,1,False)
	if room_temp_a is not None:	
		self.publish('room_temp_a',room_temp_a, precision=1)

	##########
	# 21 => calculated setpoint circuit A / N/A/ / Increment 1 / Units 0.1 deg C
	calc_setpoint_a = self.get_value(instrument,21,1,False)
	if calc_setpoint_a is not None:	
		self.publish('calc_setpoint_a',calc_setpoint_a, precision=1)

	##########
	# 62 => dwh temperature / 0 => 1500 / Increment 1 / Units 0.1 deg C
	dhw_temp = self.get_value(instrument,62,1,False)
	if dhw_temp is not None:	
		self.publish('dhw_temp',dhw_temp, precision=1)

	##########
        # 74 => boiler calculated setpoint / N/A / Increment 1 / 0.1 deg C
        boiler_calc_setpoint = self.get_value(instrument,74,1,False)
	if boiler_calc_setpoint is not None:	
		self.publish('boiler_calc_setpoint',boiler_calc_setpoint, precision=1)

	##########
        # 75 => boiler mit flue temperature / -100 => 1500 / Increment 1 / 0.1 deg C
        boiler_temp = self.get_value(instrument,75,1,True)
#	# Verifie si le bit le plus haut est mis => valeur negative
#	if(int(boiler_temp) & int('1000000000000000',2) == 32768):
#		value=(int(boiler_temp) & int('0111111111111111',2))/-10.0
#	else:
#		value=boiler_temp/10.0
	if boiler_temp is not None:
		self.publish('boiler_temp',boiler_temp, precision=1)

	##########
	# 307 => fan speed / 0 => 10000 / Increment 1 / rev/min
	fan_speed = self.get_value(instrument,307,0,False)
	if fan_speed is not None:	
		self.publish('fan_speed',fan_speed)

	##########
	# 437 => water pressure / 0 => 100 / Increment 1 / 0.1 Bar
	water_pressure = self.get_value(instrument,437,1,False)
	if water_pressure is not None:	
		self.publish('water_pressure',water_pressure, precision=1)

	##########
	# 465 => failure code
	failure_code = self.get_value(instrument,465,0,False)
	if failure_code is not None:	
		self.publish('failure_code',failure_code, precision=0)

	##########
	# 467 => temperature panneau solaire / 0 => 100 / Increment 1 / 0.1 Bar
	solar_pannel_temp = self.get_value(instrument,467,0,False)
	if solar_pannel_temp is not None:	
		# Verifie si le bit le plus haut est mis => valeur negative
		if(int(solar_pannel_temp) & int('1000000000000000',2) == 32768):
			value=(int(solar_pannel_temp) & int('0111111111111111',2))/-10.0
		else:
			value=solar_pannel_temp/10.0
		self.publish('solar_pannel_temp',value, precision=1)

	##########
	# 468 => temperature ballon solaire / 0 => 100 / Increment 1 / 0.1 Bar
	solar_tank_temp = self.get_value(instrument,468,1,False)
	if solar_tank_temp is not None:	
		self.publish('solar_tank_temp',solar_tank_temp, precision=1)

	##########
	# 500 => Alarme active ou non / 0 = False / 1 = True
	alarm = self.get_value(instrument,500,0,False)
	if alarm is not None:	
		self.publish('alarm',alarm, precision=0)

	##########
	# 607 => boiler return temperature / 0 => 1500 / Increment 1 / 0.1 deg C
	boiler_return_temp = self.get_value(instrument,607,1,False)
	if boiler_return_temp is not None:	
		self.publish('boiler_return_temp',boiler_return_temp, precision=1)

        return None
