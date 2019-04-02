class Node:
  def __init__(self, id, location):
    self.ID = id
    self.Location = location

  def __str__(self):
    return f"{self.ID}\t{self.Location}"