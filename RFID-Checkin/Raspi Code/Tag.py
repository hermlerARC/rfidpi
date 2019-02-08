'''
Written by Dominique Stepek
RFID Logging Software

Description:
Handles tags read by scanning manager as well as denotes the physical location of Raspberry PI.

Edited on: January 31, 2019
'''


import datetime

class tag:
    def __init__(self, epc, status, rssi):
        self.EPC = epc
        self.Status = status
        self.Location = "North Main Door" # Example location
        self.Time = datetime.datetime.now()
        self.RSSI = rssi
    def to_json(self):
        obj = {
            "EPC" : self.EPC,
            "Time" : str(self.Time.isoformat()),
            "Status" : self.Status,
            "Location" : self.Location,
            "RSSI" : self.RSSI
        }
        return obj
        
