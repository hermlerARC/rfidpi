'''
Written by Dominique Stepek
RFID Logging Software

Description:
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: January 31, 2019
'''

import datetime, json, Tag, time, board
from adafruit_hcsr04 import HCSR04

def create_tags(all_tag_data, status):
    all_tags = []
    
    for tag_data in all_tag_data: # Loop through each TagReadData object
        epc = str(tag_data.epc, 'utf-8')# Encode epc from byte to string
        all_tags.append(Tag.tag(epc, status, tag_data.rssi).to_json()) # Create tag object from epc and status and get json representation
        
    return all_tags

def scanning_manager(pipe, read_pipe):
	sonar1 = HCSR04(trigger_pin=board.D18,echo_pin=board.D24)
	sonar2 = HCSR04(trigger_pin=board.D17,echo_pin=board.D23)
	
	trip_time = None
	tripped_sensor = None
	active_tags = []
	
	while True:
		s1_val = sonar1.distance
		s2_val = sonar2.distance
		print(s1_val)
		print(s2_val)
		
		'''
		if tripped_sensor == None:
			if s1_val < 150:
				trip_time = datetime.datetime.now()
				tripped_sensor = 'in'
			elif s2_val < 150:
				trip_time = datetime.datetime.now()
				tripped_sensor = 'out'
		elif (datetime.datetime.now() - trip_time).total_seconds() < 3:
			if s1_val < 150 and tripped_sensor == 'out':
				#pipe.send(create_tags(read_pipe.recv(), 'in'))
				print('heading in')
				tripped_sensor = None
				trip_time = None
			elif s2_val < 150 and tripped_sensor == 'in':
				#pipe.send(create_tags(read_pipe.recv(), 'out'))
				print('heading out')
				tripped_sensor = None
				trip_time = None
		else:
			tripped_sensor = None
			trip_time = None
		'''
