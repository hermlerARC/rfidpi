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
            
        self.__status = Laser.Status.Stopped
        
    @property
    def Opposite(self):
        return Laser.Type.In if self.__type == Laser.Type.Out else Laser.Type.In
    
    @property
    def Value(self):
        return GPIO.input(self.__pin)

    def Start(self, callback):
        if self.__status == Laser.Status.Stopped:
            GPIO.setup(self.__pin, GPIO.IN)
            self.__callback = callback
            self.__status = Laser.Status.Running
            
            threading.Thread(target=self.__run).start()
            
    def Pause(self):
        if self.__status == Laser.Status.Running:
            self.__status = Laser.Status.Paused
            
    def Unpause(self):
        if self.__status == Laser.Status.Paused:
            self.__status = Laser.Status.Running
            
    def Stop(self):
        self.__status = Laser.Status.Stopped
        
    def __run(self):
        while True:
            if self.__status == Laser.Status.Running and not GPIO.input(self.__pin) and hasattr(self.__callback, '__call__'):
                callback(self.__type)
            elif self.__status == Laser.Status.Paused:
                continue
            elif self.__status == Laser.Status.Stopped:
                break
            
            
class LaserManager:
    def __init__(self):
        self.__running = False
        self.__lasers = []
        
    def StartLasers(self, callback):
        if not self.__running:
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
        self.__in_laser.Stop()
        self.__out_laser.Stop()
        GPIO.cleanup()