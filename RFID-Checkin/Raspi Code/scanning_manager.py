'''
Written by Dominique Stepek
RFID Logging Software

Description:
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: January 31, 2019
'''

import datetime, json, mercury, Tag

def get_tags(status, reader): 
    all_tags = []
    all_tag_data = reader.read() # Read every tag near RFID reader
    
    for tag_data in all_tag_data: # Loop through each TagReadData object
        epc = str(tag_data.epc, 'utf-8')# Encode epc from byte to string
        all_tags.append(Tag.tag(epc, status).to_json()) # Create tag object from epc and status and get json representation
        
    return all_tags

def scanning_manager(pipe):

    # Connect to ThingMagic RFID Reader through USB
    # TODO: Figure out how to connect reader through USB
    reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
    reader.set_region('NA')

    '''
    ~~~ Tag Reading Algorithm ~~~

    1. Check if either the inside or outside sensor has been previously tripped, if so skip to Step 4.
    2. If no sensor has been previously tripped, check if either sensor is currently tripped
    3. If a sensor is currently tripped, store time in a variable, note that the sensor has been tripped,
        read and store RFID tags. Go to Step 1
    4. If a sensor has been previously tripped and the time between the current and past trip time is less
        than 3 seconds, continue to Step 5. Otherwise, reset previous trip time and tripped sensor. Go to Step 1
    5. If a sensor is currently being tripped and the previous tripped sensor is the opposite sensor,
        send the stored RFID tags over the pipe. Go to Step 1
    '''

    trip_time = None
    tripped_sensor = None
    active_tags = []

    while True:
        if tripped_sensor == None:
            if sensor_in.value < 1000: 
                trip_time = datetime.datetime.now()
                tripped_sensor = "in"
                active_tags = tag.get_tags('out', reader) 
            elif sensor_out.value < 1000: 
                trip_time = datetime.datetime.now()
                tripped_sensor = "out"
                active_tags = tag.get_tags('in', reader) 
        elif (datetime.datetime.now() - trip_time).total_seconds() < 3: 
            if (sensor_in.value < 1000 and tripped_sensor == "out") or (sensor_out.value < 1000 and tripped_sensor == "in"):
                pipe.send(json.dumps(active_tags))
        else:
            trip_time = None
            tripped_sensor = None
