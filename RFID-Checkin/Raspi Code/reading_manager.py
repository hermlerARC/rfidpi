'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: February 19, 2019
'''

import mercury, time

def read_once(reader):
    while True: # Attempts to return list of tags infinitely
        try:
            all_tags = []
            tag_data = reader.read() # Read tags from RFID reader. Can cause RuntimeError if unable to talk to reader.

            for tag in tag_data:
                epc = str(tag.epc, 'utf-8') # Converts EPC from tag of type byte[] to string.
                rssi = tag.rssi # Receives signal strength of tag
                all_tags.append([epc, rssi])
                
            return all_tags
            break
        except RuntimeError as err:
            print('Problem reading from RFID reader. Attempting to reconnect to reader.')
            print(err)
        
def test_reader(reader):
	try:
		while True:
			print(read_once(reader))
			time.sleep(1)
	except KeyboardInterrupt:
		print('Ending RFID reader test.')

def reading_manager(pipe, reader):
    while True:
        if pipe.recv() == 'read': # Blocks thread until told to read
            pipe.send(read_once(reader)) # Sends list of tags through pipe
