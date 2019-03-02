'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: February 19, 2019
'''

import mercury, time, threading

lock = threading.Lock() # Blocks thread when accessing tags list
tags = [] # List that holds tags to send to scanning_manager

def read_once(reader):
    all_tags = []
    tag_data = reader.read() # Read tags from RFID reader. Can cause RuntimeError if unable to talk to reader.

    for tag in tag_data:
        epc = str(tag.epc, 'utf-8') # Converts EPC from tag of type byte[] to string.
        rssi = tag.rssi # Receives signal strength of tag
        all_tags.append([epc, rssi])
        
    return all_tags
        
def test_reader(reader):
    try:
        while True:
            print(reader.get_power_range())
            print(read_once(reader))
            time.sleep(2)
    except KeyboardInterrupt:
        print('Ending RFID reader test.')
        
def read(reader):
    global tags
    while True:
        current_tags = read_once(reader) # Reads EPCs and RSSIs from RFID reader
        
        lock.acquire(False)
        
        # Prevent tags list from taking too much memory by maximizing its size to 10 objects
        if len(tags) > 10: 
            tags.pop(0)
            
        tags.append(current_tags)
        lock.release()
        time.sleep(0.5)

def reading_manager(pipe, reader):
    global tags
    t = threading.Thread(target=read, args=(reader,))
    t.daemon = True
    t.start()
    while True:
        if pipe.recv() == 'read': # Blocks thread until told to read
            lock.acquire()
            pipe.send(tags.pop()) # Sends list of tags through pipe
            lock.release()
