import enum

class Status(enum.Enum):
  Running = 0
  Stopped = 1

  def __str__(self):
    return str(self.name)

class Node:
  def __init__(self, id, location, stat = Status.Stopped):
    self.ID = id
    self.Location = location
    self.Status = stat

  def __str__(self):
    return f"{self.ID}\t{self.Location}\t{str(self.Status)}"