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

def read_once(reader):
    all_tags = []
    tag_data = reader.read() # Read tags from RFID reader. Can cause RuntimeError if unable to talk to reader.
    
    for tag in tag_data:
        epc = str(tag.epc, 'utf-8') # Converts EPC from tag of type byte[] to string.
        print("{}\t{}".format(datetime.datetime.now(),epc)
##        if epc == 'E20035636B938EF0E6B1963B':
##            continue
        rssi = tag.rssi # Receives signal strength of tag
        all_tags.append([epc, rssi])
        
    return all_tags
        
def test_reader(reader):
    global READ_SPEED
    term = True
    
    def test():
        while term:
            read = read_once(reader)
            if len(read) > 0:
                pass
                #print("{}\t{}".format(datetime.datetime.now(),read_once(reader)))
            time.sleep(1/READ_SPEED)
        
    threading.Thread(target=test).start()
    input()
    print("Stopping Test")
    term = False
        
def read(reader):
    global tags
    
    while True:
        current_tags = None
        while True:
            current_tags = read_once(reader)
            
            if len(current_tags) > 0:
                print('got tags')
                current_tags = read_once(reader) # Reads EPCs and RSSIs from RFID reader
                break
            
        lock.acquire()
        tags = [current_tags, datetime.datetime.now()]
        lock.release()

def reading_manager(pipe, reader):
    global tags
    
    t = threading.Thread(target=read, args=(reader,))
    t.daemon = True
    t.start()
    
    while True:
        pass_time = pipe.recv()
        ctime = datetime.datetime.now()
        
        lock.acquire()
        print(tags)
        
        if (pass_time - tags[1]).total_seconds() < 1:
            pipe.send(tags) # Send most recent list of tags
            
        lock.release()
        
        print('sent tags after {} seconds'.format((datetime.datetime.now() - ctime).total_seconds()))
