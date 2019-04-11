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
    return f"{self.ID},{self.Location},{str(self.Status)}"


ErrorCode = {
  0x0 : "Attempted to start a node that is already running",
  0x1 : "Unknown"
}