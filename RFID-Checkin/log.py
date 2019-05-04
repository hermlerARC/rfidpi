'''
RFID Logging Software

Description (log.py): 
Log class

Contributors:
Dom Stepek

Edited on: May 4, 2019
'''

import rfidtag, datetime, re, enum

class Log:
  __DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'
  __DICT_VALUES = ['Timestamp', 'EPC', 'Status', 'Owner', 'Description', 'Location', 'Extra']

  class Status(enum.Enum):
    In = 0
    Out = 1
    Unknown = 2

    def __str__(self):
      return str(self.name)

    def GetStatus(val):
      if isinstance(val, int):
        return Log.Status(val)
      elif isinstance(val, str):
        return Log.Status[val.title()]
      elif isinstance(val, Log.Status):
        return val
      else:
        return ValueError

  def __init__(self, *args, **kwargs):
    """
    kwargs:
      Timestamp: datetime, when the tag was reported
      EPC: str, EPC of tag
      Status: TagStatus, direction the tag was moving
      Owner: str, to whom the tag is associated
      Description: str, what does the tag represent
      Location: str, where the tag was scanned
      Extra: str, additional info
    """
    if all(x in kwargs for x in Log.__DICT_VALUES):
      self.__dict__ = kwargs
      self.Status = Log.Status.GetStatus(self.Status)

      if isinstance(self.Timestamp, str):
        self.Timestamp = datetime.datetime.strptime(self.Timestamp, Log.__DATETIME_FORMAT)

      if isinstance(self.Timestamp, datetime.datetime) and isinstance(self.Status, Log.Status):
        return
    else:
      if len(args) == 1 and ',' in args[0]:
        self.__init__(*re.sub(r'(?<=,)\s', '', args[0]).split(','))
        return
      elif len(args) == 3 and isinstance(args[1], rfidtag.RFIDTag):
        self.__init__(args[0], args[1].EPC, args[1].Status.Value, args[1].Owner, args[1].Description, args[2], args[1].Extra)
        return
      elif len(args) == len(Log.__DICT_VALUES):
        self.__init__(Timestamp=args[0], EPC=args[1], Status=args[2], Owner=args[3], Description=args[4], Location=args[5], Extra=args[6])
        return
          
    raise ValueError

  def __str__(self):
    return f"{self.Timestamp.strftime(Log.__DATETIME_FORMAT)},{self.EPC},{str(self.Status)},{self.Owner},{self.Description},{self.Location},{self.Extra}"

