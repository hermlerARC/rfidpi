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
    
    self.Timestamp = datetime.datetime.now()
      
  def to_object(self):
  """
  Deprecated. Use Tag.__dict__ instead
  """
    return {
        "EPC" : self.EPC,
        "Status" : self.Status.name,
        "RSSI" : self.RSSI
    }