'''
RFID Logging Software

Description (scanning_manager.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: February 19, 2019
'''

import datetime, json, Tag, time, sensors

SPEED_OF_SOUND = 34300 # centimeters/second

def create_tags(tag_list, status):
    print(tag_list)
    all_tags = []
    
    for x in tag_list: # Loop through each TagReadData object
        all_tags.append(Tag.tag(x[0], status, x[1]).to_json()) # Create tag object from epc and status and get json representation
            
    return all_tags

def scanning_manager(pipe, read_pipe):
    sensors.setup() # Connect GPIO pins to sonar sensors.
    
    threshold_distance = 200 # Max distance to read in centimeters before sensors are considered 'tripped'.
    threshold_time = 3 # Max seconds to wait for object to pass both sensors.
    sleep_time = threshold_distance / SPEED_OF_SOUND # Wait time before each call to sensors.get_sensor_value() to allow for sensors to read properly
    
    '''
    ~~ Tag Reading Algorithm ~~
    1. Get current time and store in a variable 'x'
    2. If either sensor reads below a threshold distance value, go to step 3. Otherwise, go to step 6.
    3. If a threshhold time is reached between current time and 'x', go to step 4. Otherwise, go to step 5.
    4. If other sensor reads below a threshold distance, read for RFID tags and send to reporting_manager tags marked with the last sensor tripped.
    5. Pause script for a sleep time and go to step 3.
    6. Pause script for a sleep time and go to step 2.
    '''
    
    while True:
        ctime = datetime.datetime.now()
        
        s1 = sensors.get_sensor_value('in')
        
        if s1 < threshold_distance:
            while (datetime.datetime.now() - ctime).total_seconds() < threshold_time:
                if (sensors.get_sensor_value('out') < threshold_distance):
                    read_pipe.send('read')
                    cc = datetime.datetime.now()
                    pipe.send(json.dumps(create_tags(read_pipe.recv(), 1)))
                    print("performance: {}".format(datetime.datetime.now()-cc))
                    break
                time.sleep(sleep_time)
        
        if sensors.get_sensor_value('out') < threshold_distance:
            while (datetime.datetime.now() - ctime).total_seconds() < threshold_time:
                if (sensors.get_sensor_value('in') < threshold_distance):
                    read_pipe.send('read')
                    cc = datetime.datetime.now()
                    pipe.send(json.dumps(create_tags(read_pipe.recv(), 0)))
                    print("performance: {}".format(datetime.datetime.now()-cc))
                    break
                time.sleep(sleep_time)
                                
        time.sleep(1)
