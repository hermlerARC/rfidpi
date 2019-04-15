'''
RFID Logging Software

Description (Tags.py):
Handles tags read by scanning manager as well as denotes the physical location of Raspberry PI.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: March 21, 2019
'''

import datetime, enum

DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'

class TagStatus(enum.Enum):
  In = 0
  Out = 1
  Unknown = 2

class Tag:
  def __init__(self, epc, status, rssi):
    self.Time = datetime.datetime.now()
    self.RSSI = rssi

    if isinstance(epc, bytes):
      self.EPC = str(epc, 'utf-8')
    elif isinstance(epc, str):
      self.EPC = epc
      
    if isinstance(status, TagStatus):
      self.Status = status
    elif isinstance(status, int):
      self.Status = TagStatus(status)
    elif isinstance(status, str):
      self.Status  = TagStaus[status.title()]
      
  def to_object(self):
    return {
        "EPC" : self.EPC,
        "Time" : str(self.Time.strftime(DATETIME_FORMAT)),
        "Status" : self.Status.name,
        "RSSI" : self.RSSI
    }