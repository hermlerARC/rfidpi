'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: February 19, 2019
'''

import threading, datetime

lock = threading.Lock() # Blocks thread when accessing tags list
tags = [] # List that holds tags to send to scanning_manager

def read_once(reader):
    all_tags = []
    tag_data = reader.read() # Read tags from RFID reader. Can cause RuntimeError if unable to talk to reader.

    for tag in tag_data:
        epc = str(tag.epc, 'utf-8') # Converts EPC from tag of type byte[] to string.
        if epc == 'E20035636B938EF0E6B1963B':
            continue
        rssi = tag.rssi # Receives signal strength of tag
        all_tags.append([epc, rssi])
        
    return all_tags
        
def test_reader(reader):
    try:
        while True:
            print(reader.get_power_range())
            print(read_once(reader))
    except KeyboardInterrupt:
        print('Ending RFID reader test.')
        
def read(reader):
    global tags
    while True:
        current_tags = read_once(reader) # Reads EPCs and RSSIs from RFID reader
        
        lock.acquire()
        
        # Prevent tags list from taking too much memory by maximizing its size to 10 objects
        if len(tags) > 10: 
            tags.pop(0)
            
        if current_tags == []:
            lock.release()
            continue
        tags.append(current_tags)
        lock.release()

def reading_manager(pipe, reader):
    global tags
    t = threading.Thread(target=read, args=(reader,))
    t.daemon = True
    t.start()
    while True:
        if pipe.recv() == 'read': # Blocks thread until told to read
            ctime = datetime.datetime.now()
            while True:
                try:
                    lock.acquire()
                    pipe.send(tags.pop()) # Sends list of tags through pipe
                    print('sent tags after {} seconds'.format((datetime.datetime.now() - ctime).total_seconds()))
                    lock.release()
                    break
                except:
                    continue
