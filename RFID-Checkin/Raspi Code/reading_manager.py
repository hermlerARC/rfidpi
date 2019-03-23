'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

import threading, datetime, time

lock = threading.Lock() # Blocks thread when accessing tags list
tags = [] # List that holds tags to send to scanning_manager
READ_SPEED = 10

def test_reader(reader):
    print('starting')
    def print_tag(tag):
        print("{}\t{}".format(datetime.datetime.now(), str(tag.epc, 'utf-8')))
        
    reader.start_reading(print_tag, on_time=250, off_time=0)
    print('begin')
    
    while input() != '\n':
        pass
    reader.stop_reading()
    
    
def read(reader):
    global tags
    
    def process_tags(tag):
        lock.acquire()
        tags.append([str(tag.epc, 'utf-8'), tag.rssi, datetime.datetime.now()])
        print(tags)
        lock.release()
    
    print('here')
    reader.start_reading(process_tags, on_time=250, off_time=0)

    while input() != '\n':
        pass
    reader.stop_reading()

def reading_manager(pipe, reader):
    global tags
    
    threading.Thread(target=read,args=(reader,)).start()
    
    while True:
        pass_time = pipe.recv()
        
        lock.acquire()
        print(tags)
        #proper = list(filter(lambda reading: (reading[2] - pass_time).total_seconds() < 2, tags))
        tags.clear()
        lock.release()
        #pipe.send(proper)