import enum

class Status(enum.Enum):
  In = 0
  Out = 1
  Unknown = 2

  def __str__(self):
    return str(self.name)

class RFIDTag:		
  def __init__(self, epc, status, owner, description, node, extra):
    self.EPC = epc
    self.Status = status
    self.Owner = owner
    self.Description = description
    self.Extra = extra
    self.Node = node

  def __str__(self):
    return f"{self.EPC}\t{str(self.Status)}\t{self.Owner}\t{self.Description}\t{self.Node.Location}\t{self.Extra}"