import json, node, rfidtag

class Log(rfidtag.RFIDTag):
  def __init__(self, timestamp, epc, status, owner, description, node, extra):
    rfidtag.RFIDTag.__init_(self, epc, status, owner, description, node, extra)
    self.Timestamp = timestamp

  def __init__(self, tag, timestamp, node):
    super().__init__(tag.EPC, tag.Status, tag.Owner, tag.Description, tag.Node, tag.Extra)
    self.Timestamp = timestamp
    self.Node = node

  def __str__(self):
    return "{}\t{}".format(self.Timestamp, super().__str__())