'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

import threading, datetime

lock = threading.Lock() # Blocks thread when accessing tags list
tags = [] # List that holds tags to send to scanning_manager
TIME_THRESHOLD = 1 # In seconds, increase of time range where tags were read. 

def test_reader(reader):
    print('starting')
    
    def print_tag(tag):
        print("{}\t{}".format(datetime.datetime.now(), str(tag.epc, 'utf-8')))
        
    reader.start_reading(print_tag, on_time=250, off_time=0)
    print('begin')
    
    while input("Enter to exit") != '\n':
        pass
    reader.stop_reading()
    
    
def read(reader):
    global tags
    
    def process_tags(tag):
        lock.acquire()
        tags.append([str(tag.epc, 'utf-8'), tag.rssi, datetime.datetime.now()])
        lock.release()
    
    reader.start_reading(process_tags, on_time=250, off_time=0)

    while input("Enter to exit") != '\n':
        pass
    reader.stop_reading()

def reading_manager(pipe, reader):
    global tags
    global TIME_THRESHOLD
    
    threading.Thread(target=read,args=(reader,)).start()
    
    while True:
        '''
        Wait for a read signal from the scanning manager.
        Message will give the time range of the tripped sensors.
        Increase the range by TIME_THRESHOLD.
        '''
        times = pipe.recv()
        times = [times[0] - datetime.timedelta(seconds=TIME_THRESHOLD/2), times[1] + datetime.timedelta(seconds=TIME_THRESHOLD/2)]

        lock.acquire()
        if len(tags) > 0:  
            ranged_tags = list(filter(lambda x: x[2] > times[0] and x[2] < times[1], tags)) # Get all tags within the time range
            
            lock.release()
            
            # Discard any duplicate tag reads.
            adjusted_tags = []
            for x in ranged_tags:
              if x[0] not in list(map(lambda y: y[0], adjusted_tags)):
                adjusted_tags.append(x)
                
            pipe.send(adjusted_tags) # Release tags back over the pipe
        else:
            lock.release()