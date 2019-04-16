import rfidtag, datetime

DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'

class Log(rfidtag.RFIDTag):
  def __init__(self, timestamp, epc, status, owner, description, location, extra):
    self.Timestamp = timestamp
    self.EPC = epc
    self.Status = status
    self.Owner = owner
    self.Description = description
    self.Location = location
    self.Extra = extra

  def __str__(self):
    return f"{self.Timestamp.strftime(DATETIME_FORMAT)},{self.EPC},{str(self.Status)},{self.Owner},{self.Description},{self.Node.Location},{self.Extra}"

def convert_to_log(*args):
  """
  Converts arguments to a log object

  Args:\n
    [RFIDTag, DateTime]\n
    [str, list<Node>]
      arg0: str, must be formatted as "timestamp,epc,status,owner,description,location,extra"
      arg1: list<Node>, all nodes
  Returns: Log
  """
  if isinstance(args[0], rfidtag.RFIDTag) and isinstance(args[1], datetime.datetime):
    return Log(args[1], args[0].EPC, args[0].Status, args[0].Owner, args[0].Description, args[0].LastLocation, args[0].Extra)
  elif isinstance(args[0], str):
    fields = args[0].split(sep=',')

    if len(fields) == 7:
      timestamp = datetime.datetime.strptime(fields[0], "%d/%m/%Y %H:%M:%S")
      return Log(timestamp, fields[1], fields[2], fields[3], fields[4], fields[5], fields[6])
    else:
      print(args[0])
      print('Cannot cast text to Log object')
      raise ValueError
