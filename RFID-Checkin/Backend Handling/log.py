import rfidtag, re, datetime, node

class Log(rfidtag.RFIDTag):
  def __init__(self, timestamp, epc, status, owner, description, node, extra):
    rfidtag.RFIDTag.__init__(self, epc, status, owner, description, node, extra)
    self.Timestamp = timestamp

  def __repr__(self):
    return f"{self.Timestamp.strftime('%d/%m/%Y %H:%M:%S')},{str(self.Status)},{self.EPC},{self.Owner},{self.Description},{self.Node.Location},{self.Extra}"

  def __str__(self):
    return f"{self.Timestamp.strftime('%d/%m/%Y %H:%M:%S')},{str(self.Status)},{self.EPC},{self.Owner},{self.Description},{self.Node.Location},{self.Extra}"

def convert_to_log(*args):
  """
  Converts arguments to a log object

  Args:\n
    [RFIDTag, DateTime, Node]\n
    [str, list<Node>]
      arg0: str, must be an instance of repr(Log)
      arg1: list<Node>, all nodes
  Returns: Log
  """
  if isinstance(args[0], rfidtag.RFIDTag) and isinstance(args[1], datetime.datetime) and isinstance(args[2], node.Node):
    return Log(args[1], args[0].EPC, args[0].Status, args[0].Owner, args[0].Description, args[2], args[0].Extra)
  elif isinstance(args[0], str) and isinstance(args[1], list):
    capture = re.match(r"(?:(?P<timestamp>.+?),)(?:(?P<status>.+?),)(?:(?P<epc>.+?),)(?:(?P<owner>.+?),)(?:(?P<description>.+?),)(?:(?P<location>.+?),)(?:(?P<extra>.+))", args[0])
    
    if capture:
      try:
        curr_node = next(n for n in args[1] if n.Location == capture.group('location'))
        timestamp = datetime.datetime.strptime(capture.group('timestamp'), "%d/%m/%Y %H:%M:%S")
        return Log(timestamp, capture.group('epc'), capture.group('status'), capture.group('owner'), capture.group('description'), curr_node, capture.group('extra'))
      except:
        print(args[0])
        print('Cannot cast text to Log object')
        raise ValueError
