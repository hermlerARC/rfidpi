import re
from paho.mqtt import publish

class ActionLawsuit:
  def __init__(self, title, owner):
    self.__title = title
    self._owner = owner

  @property
  def Title(self):
    return self.__title

  @property
  def Owner(self):
    return self._owner

  @Title.setter
  def SetTitle(self, value):
    self.__title = value

x = range(0, 10)
y = [ActionLawsuit("dom", "in"), ActionLawsuit("Matt", "Out")]

a = "hac"
for j in y:
  j.SetTitle = "hac"


print([[i.Title, i.Owner] for i in y])