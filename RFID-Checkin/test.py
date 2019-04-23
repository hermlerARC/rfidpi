from node_enums import *
import pickle, datetime
from paho.mqtt import client


class ActionLawsuit:
  def __init__(self, title, owner):
    self.__title = title
    self.__owner = owner

  @property
  def Title(self):
    return self.__title

als = [ ["dom", 'jackson'], ['das', 'hehe'], ['yup', 'nope']]

alr = [ActionLawsuit(a[0],a[1]) for a in als][0:]

for i in range(10, 0, -1):
  print(i)
