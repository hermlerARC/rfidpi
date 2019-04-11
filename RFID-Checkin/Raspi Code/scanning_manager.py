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
process_running = True
sensor_testing = False

def set_testing(val):
    global sensor_testing
    sensor_testing = val

def set_process(val):
    global process_running
    process_running = val
    
def create_tags(tag_list, status):
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
    global process_running

    active_threads = [sensors.begin_reading(0, read_sensors), sensors.begin_reading(1, read_sensors)]

    while process_running:
        sensor = read_status.get() # First sensor to report being tripped
        current_time = datetime.datetime.now()
        end_time = None
        second_read = None
        activated = False
        read_response = None
        
        sensors.set_read_status(active_threads[sensor], 0) # Pauses sensor from continuously reading
        
        while True:
            if (datetime.datetime.now() - current_time).total_seconds() >= THRESHOLD_TIME:
                # Clears the queue of any garbage reads
                with read_status.mutex:
                    read_status.queue.clear()
                break
            try:
                second_read = read_status.get(timeout=THRESHOLD_TIME) # Wait for a threshold time sensor to drop below the THRESHOLD_DISTANCE
                if second_read == (int(not sensor)): # Prevents first sensor from being double read
                    end_time = datetime.datetime.now()    
                    activated = True
                    break
            except queue.Empty: # If the queue remains empty for a threshold time
                # Clears the queue of any garbage reads
                with read_status.mutex:
                    read_status.queue.clear()
                break
            
        # Tells reading manager to send a list of tag readings, converts object to JSON, and sends data to reporting manager 
        if activated:
            activated = False 
            print('heading {}'.format('in' if int(not sensor) else 'out'))
            read_pipe.send([current_time, end_time])
            
            read_response = read_pipe.recv()
            if len(read_response) > 0:
                reporting_pipe.send(json.dumps(create_tags(read_response, int(not sensor))))
        else:
            print('unknown direction')
            read_pipe.send([current_time, current_time + datetime.timedelta(seconds=THRESHOLD_TIME)])
            
            read_response = read_pipe.recv()
            
            if len(read_response) > 0:
                reporting_pipe.send(json.dumps(create_tags(read_response, 2)))
            
        sensors.set_read_status(active_threads[sensor], 1) # Resumes the paused sensor
    
    sensors.set_read_status(active_threads[0], 2)
    sensors.set_read_status(active_threads[1], 2)