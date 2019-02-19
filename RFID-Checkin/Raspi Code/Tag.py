'''
RFID Logging Software

Description (Tags.py):
Handles tags read by scanning manager as well as denotes the physical location of Raspberry PI.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: February 19, 2019
'''


import datetime

class tag:
    def __init__(self, epc, status, rssi):
        self.EPC = epc
        self.Status = status
        self.Time = datetime.datetime.now()
        self.RSSI = rssi
        
    def to_json(self):
        obj = {
            "EPC" : self.EPC,
            "Time" : str(self.Time.isoformat()),
            "Status" : self.Status,
            "RSSI" : self.RSSI
        }
        return obj
        
