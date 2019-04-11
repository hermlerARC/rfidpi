'''
RFID Logging Software

Description (Tags.py):
Handles tags read by scanning manager as well as denotes the physical location of Raspberry PI.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: March 21, 2019
'''


import datetime

DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'

class tag:
    def __init__(self, epc, status, rssi):
        self.EPC = epc
        self.Status = status
        self.Time = datetime.datetime.now()
        self.RSSI = rssi
        
    def to_json(self):
        obj = {
            "EPC" : self.EPC,
            "Time" : str(self.Time.strftime(DATETIME_FORMAT)),
            "Status" : self.Status,
            "RSSI" : self.RSSI
        }
        return obj
        
