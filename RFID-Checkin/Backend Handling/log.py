import rfidtag

class Log(rfidtag.RFIDTag):
  def __init__(self, timestamp, epc, status, owner, description, node, extra):
    rfidtag.RFIDTag.__init__(self, epc, status, owner, description, node, extra)
    self.Timestamp = timestamp

  def __init__(self, tag, timestamp, node):
    rfidtag.RFIDTag.__init__(self, tag.EPC, tag.Status, tag.Owner, tag.Description, node, tag.Extra)
    self.Timestamp = timestamp

  def __repr__(self):
    return f"{self.Timestamp},{str(self.Status)},{self.EPC},{self.Owner},{self.Description},{self.Node.Location},{self.Extra}"

  def __str__(self):
    return f"{self.Timestamp.strftime('%d/%m/%Y %H:%M:%S')}\t{str(self.Status)}\t{self.EPC}\t{self.Owner}\t{self.Description}\t{self.Node.Location}\t{self.Extra}"