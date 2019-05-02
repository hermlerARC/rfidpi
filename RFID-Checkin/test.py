import re
from paho.mqtt import publish

class ActionLawsuit:
  def __init__(self, title, owner):
    self.__title = title
    self.__owner = owner

  @property
  def Title(self):
    return self.__title

publish.single("reader/UPOGDU/response", payload="works!", qos=1, hostname="broker.mqttdashboard.com",
    port=8000, transport="websockets")
