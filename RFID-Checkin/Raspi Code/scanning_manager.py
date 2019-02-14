'''
Written by Dominique Stepek
RFID Logging Software

Description:
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: January 31, 2019
'''

import datetime, json, Tag, time, sensors

def create_tags(tag_list, status):
    all_tags = []
    
    for x in tag_list: # Loop through each TagReadData object
        all_tags.append(Tag.tag(x[0], status, x[1]).to_json()) # Create tag object from epc and status and get json representation
        
    return all_tags

def scanning_manager(pipe, read_pipe):
	sensors.setup()
	threshold =  100
	
	trip = []
	active_tags = []
	
	while True:
		ctime = datetime.datetime.now()
		exit_loop = False
		
		if sensors.get_sensor1_value() < threshold:
			exit_loop = False
			while (datetime.datetime.now() - ctime).total_seconds() < 3 and not exit_loop:
				if (sensors.get_sensor2_value() < threshold):
					pipe.send(json.dumps(create_tags(read_pipe.recv(), 'out')))
					time.sleep(.001)
					
		if sensors.get_sensor2_value() < threshold:
			exit_loop = False
			while (datetime.datetime.now() - ctime).total_seconds() < 3 and not exit_loop:
				if (sensors.get_sensor1_value() < threshold):
					pipe.send(json.dumps(create_tags(read_pipe.recv(), 'in')))
					time.sleep(.001)
		time.sleep(.001)
