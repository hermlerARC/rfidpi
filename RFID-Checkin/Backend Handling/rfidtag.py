import enum, node as Node

class Status(enum.Enum):
  In = 0
  Out = 1
  Unknown = 2

  def __str__(self):
    return str(self.name)

class RFIDTag:		
  def __init__(self, epc, status, owner, description, last_location, extra):
    self.EPC = epc
    self.Status = status
    self.Owner = owner
    self.Description = description
    self.Extra = extra
    self.LastLocation = last_location

  def __str__(self):
    return f"{self.EPC},{str(self.Status)},{self.Owner},{self.Description},{self.LastLocation},{self.Extra}"