import enum, re

class RFIDTag:
  __DICT_VALUES = ['EPC', 'Status', 'Owner', 'Description', 'LastLocation', 'Extra']

  class Status(enum.Enum):
    In = 0
    Out = 1
    Unknown = 2

    def __str__(self):
      return str(self.name)

    def GetStatus(val):
      if isinstance(val, int):
        return RFIDTag.Status(val)
      elif isinstance(val, str):
        return RFIDTag.Status[val.title()]
      elif isinstance(val, RFIDTag.Status):
        return val
      else:
        return ValueError
      
  def __init__(self, *args, **kwargs):
    if all(x in kwargs for x in RFIDTag.__DICT_VALUES):
      self.__dict__ = kwargs
      self.Status = RFIDTag.Status.GetStatus(self.Status)
      
      if isinstance(kwargs['Status'], RFIDTag.Status):
        return
    else:
      if len(args) == 1 and ',' in args[0]:
        self.__init__((*re.sub(r'(?<=,)\s', '', args[0]).split(',')))
        return
      elif len(args) == len(RFIDTag.__DICT_VALUES):
        self.__init__(EPC=args[0], Status=args[1], Owner=args[2], Description=args[3], LastLocation=args[4], Extra=args[5])
        return
          
    raise ValueError("Invalid settings for a Tag")

  def __str__(self):
    return f"{self.EPC},{str(self.Status)},{self.Owner},{self.Description},{self.LastLocation},{self.Extra}"