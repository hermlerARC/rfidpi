'''
RFID Logging Software

Description (sensors.py):
Contains Laser and LaserManager class that deals with low-level access of the photoresistor readings.

Contributors:
Dom Stepek

Edited on: May 4, 2019
'''

import RPi.GPIO as GPIO
import time, threading, enum, datetime
from multiprocessing import Process

class Laser:
  __IN_PIN = 7
  __OUT_PIN = 11

  class Type(enum.Enum):
    In = 0
    Out = 1
    
  class Status(enum.Enum):
    Running = 0
    Paused = 1
    Stopped = 2

  def __init__(self, type):
    self.__type = type
    
    # Assign the pins to the proper laser type
    if type == Laser.Type.In:
      self.__pin = Laser.__IN_PIN
    elif type == Laser.Type.Out:
      self.__pin = Laser.__OUT_PIN
        
    GPIO.setup(self.__pin, GPIO.IN)
      
  @property
  def Opposite(self):
    return Laser.Type.In if self.__type == Laser.Type.Out else Laser.Type.In

  @property
  def Value(self):
    # Pulls value of digital input from the pin.
    return GPIO.input(self.__pin)
            
class LaserManager:
  def __init__(self):
    GPIO.setmode(GPIO.BOARD)
    self.__in_laser = Laser(Laser.Type.In)
    self.__out_laser = Laser(Laser.Type.Out)

  @property
  def Lasers(self):
    return [self.__in_laser, self.__out_laser]

  @property
  def InLaser(self):
    return self.__in_laser

  @property
  def OutLaser(self):
    return self.__out_laser
  
  def StopLasers(self):
    GPIO.cleanup() # Allows for pins to be reused without conflict in future runs of the script
