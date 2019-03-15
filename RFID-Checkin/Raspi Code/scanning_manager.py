'''
RFID Logging Software

Description (scanning_manager.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: February 19, 2019
'''
import datetime, json, Tag, time, sensors, threading

SPEED_OF_SOUND = 34300 # centimeters/second

in_read = None
out_read = None
read_pipe = None
reporting_pipe = None
pipe_lock = threading.Lock()


def create_tags(tag_list, status):
    print(tag_list)
    all_tags = []
    
    for x in tag_list: # Loop through each TagReadData object
        all_tags.append(Tag.tag(x[0], status, x[1]).to_json()) # Create tag object from epc and status and get json representation
            
    return all_tags

def read_sensors(sensor, threshold):
    global read_pipe
    global reporting_pipe
    global in_read
    global out_read
    
    while True:
        if sensors.get_sensor_value(sensor) < threshold:
            if sensor == 'in':
                in_read =  datetime.datetime.now()
            elif sensor == 'out':
                out_read = datetime.datetime.now()
                
        time.sleep(0.05)
            

def scanning_manager(reporting_pipe, read_pipe):
    global in_read
    global out_read
    prev_in = []
    prev_out = []
    
    threshold_distance = 150 # Max distance to read in centimeters before sensors are considered 'tripped'.

    threading.Thread(target=read_sensors, args=('in', threshold_distance)).start()
    threading.Thread(target=read_sensors,args=('out',threshold_distance)).start()
    
    while True:
        if in_read == None or out_read == None:
            continue
        else:
            if (in_read - out_read).total_seconds() < 3 and (in_read - out_read).total_seconds() > 0:
                read_pipe.send('read')
                new_tags = create_tags(read_pipe.recv(), 0)
                #for tag in prev_in:
                    
                    
                reporting_pipe.send(json.dumps(new_tags))
                in_read = None
                out_read = None
            elif (out_read - in_read).total_seconds() < 3 and (out_read - in_read).total_seconds() > 0:
                read_pipe.send('read')
                new_tags = create_tags(read_pipe.recv(), 1)
                #for tag in prev_in:
                    
                    
                reporting_pipe.send(json.dumps(new_tags))
                in_read = None
                out_read = None