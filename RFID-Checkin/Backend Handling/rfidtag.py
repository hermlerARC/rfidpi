import json, enum

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
    return "{}\t{}\t{}\t{}\t{}\t{}".format(self.EPC, str(self.Status), self.Owner, self.Description, self.Node.Location, self.Extra)