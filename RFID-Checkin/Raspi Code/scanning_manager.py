'''
RFID Logging Software

Description (scanning_manager.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: March 21, 2019
'''
import datetime, json, Tag, sensors, queue

THRESHOLD_TIME     = 3 # Max threshold seconds to wait for someone to pass by both sensors
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
    global THRESHOLD_TIME

    active_threads = [sensors.begin_reading(0, read_sensors), sensors.begin_reading(1, read_sensors)]
    
    while True:
        sensor = read_status.get() # First sensor to report being tripped
        current_time = datetime.datetime.now()
        second_read = None
        activated = False
        
        sensors.set_read_status(active_threads[sensor], 0) # Pauses sensor from continuously reading
        
        while True:
            if (datetime.datetime.now() - current_time).total_seconds() >= THRESHOLD_TIME:
                # Resets the queue
                with read_status.mutex:
                    read_status.queue.clear() 
                break
            try:
                second_read = read_status.get(timeout=THRESHOLD_TIME) # Wait for a threshold time sensor to drop below the THRESHOLD_DISTANCE
                if second_read == (int(not sensor)): # Prevents first sensor from being double read
                    activated = True
                    break
            except queue.Empty: # If the queue remains empty for a threshold time
                # Resets the queue
                with read_status.mutex:
                    read_status.queue.clear() 
                break
            
        # Tells reading manager to send a list of tag readings, converts object to JSON, and sends data to reporting manager 
        if activated:
            print('heading {}'.format('in' if int(not sensor) == 0 else 'out'))
            activated = False 
            read_pipe.send(current_time)
            reporting_pipe.send(json.dumps(create_tags(read_pipe.recv(), int(not sensor))))
            print('sent tags')
            
        sensors.set_read_status(active_threads[sensor], 1) # Resumes the paused sensor