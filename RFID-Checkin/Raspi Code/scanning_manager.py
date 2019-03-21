'''
RFID Logging Software

Description (scanning_manager.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: February 19, 2019
'''
import datetime, json, Tag, time, sensors, queue

THRESHOLD_DISTANCE = 150 # Max distance to read in centimeters before sensors are considered 'tripped'.
read_status = queue.Queue(maxsize = 1)

def create_tags(tag_list, status):
    print(tag_list)
    all_tags = []
    
    for x in tag_list: # Loop through each TagReadData object
        all_tags.append(Tag.tag(x[0], status, x[1]).to_json()) # Create tag object from epc and status and get json representation
            
    return all_tags

def read_sensors(sensor, value):
    global THRESHOLD_DISTANCE
    global read_status
    
    if value < THRESHOLD_DISTANCE:
        read_status.put(sensor)
        

def scanning_manager(reporting_pipe, read_pipe):
    global read_status
    global THRESHOLD_DISTANCE

    active_threads = [sensors.begin_reading(0, read_sensors), sensors.begin_reading(1, read_sensors)]
    
    while True:
        sensor = read_status.get()
        
        sensors.set_read_status(active_threads[sensor], 0) # Pauses sensor from continuously reading
        second_read = read_status.get() # Wait for a second sensor to drop below the THRESHOLD_DISTANCE
        
        # Handles the possibility of read_status getting multiple reads from one sensor
        while second_read != (int(not sensor)):
            second_read = read_status.get()
            
        # Tells reading manager to send a list of tag readings, converts object to JSON, and sends data to reporting manager 
        read_pipe.send('read')
        reporting_pipe.send(json.dumps(create_tags(read_pipe.recv(), int(not sensor))))
        
        # Resumes the first sensor
        sensors.set_read_status(active_threads[sensor], 1)