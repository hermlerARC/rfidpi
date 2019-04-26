'''
RFID Logging Software

Description (sensors.py):
Contains Sensor class that gets readings from a sensor on a different thread.

Contributors:
Dom Stepek

Source code: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/

Edited on: March 21, 2019
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
        return GPIO.input(self.__pin)
            
class LaserManager:
    def __init__(self):
        self.__running = False
        GPIO.setmode(GPIO.BOARD)
        self.__in_laser = Laser(Laser.Type.In)
        self.__out_laser = Laser(Laser.Type.Out)

    @property
    def InLaser(self):
        return self.__in_laser

    @property
    def OutLaser(self):
        return self.__out_laser
    
    def StopLasers(self):
        GPIO.cleanup()
  