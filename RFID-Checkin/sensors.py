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

class SensorType(enum.Enum):
  In = 0
  Out = 1

  def __str__(self):
    return self.name
  
  @property
  def Opposite(self):
    return SensorType.Out if self == SensorType.In else SensorType.In

class SensorStatus(enum.Enum):
  Running = 0
  Paused = 1
  Stopped = 2

class SensorReading:
  def __init__(self, sensor_type, value):
    self.Timestamp = datetime.datetime.now()
    self.SensorType = sensor_type
    self.Reading = value

class Sensor:
  def __init__(self, sensor_type):
    IN_PINS = [12,16]
    OUT_PINS = [22,18]

    self.__sensor_type = sensor_type
    self.__status = SensorStatus.Stopped
    self.__pins = IN_PINS if self.__sensor_type == SensorType.In else OUT_PINS

    GPIO.setup(self.__pins[0], GPIO.OUT)
    GPIO.setup(self.__pins[1], GPIO.IN)

  def BeginReading(self, callback, read_speed = 1):
    if self.__status == SensorStatus.Running:
      raise RuntimeError('Sensor is already running')

    if self.__status == SensorStatus.Paused:
      self.__status = SensorStatus.Running
      return

    if isinstance(read_speed, int) and read_speed > 0:
      self.__read_speed = read_speed
      self.__status = SensorStatus.Running
      
      threading.Thread(target=self.__run, args=(callback,)).start()
    else:
      raise ValueError("Invalid read_speed argument: {}".format(read_speed))
 
  def StopReading(self):
    self.__status = SensorStatus.Stopped

  def PauseReading(self):
    if self.__status == SensorStatus.Running:
      self.__status = SensorStatus.Paused
      
  def UnpauseReading(self):
    if self.__status == SensorStatus.Paused:
        self.__status = SensorStatus.Running

  @property
  def Status(self):
    return self.__status

  def __run(self, callback):
    while True:
      if self.__status == SensorStatus.Running:
        if hasattr(callback, '__call__'):
          val = self.__get_sensor_value()
          sr = SensorReading(self.__sensor_type, val)
          callback(sr)
          
          if self.__read_speed <= 0:
            time.sleep(1)
          else:
            time.sleep(1) #time.sleep(1 / self.__read_speed)
            
      elif self.__status == SensorStatus.Paused:
        continue
      elif self.__status == SensorStatus.Stopped:
        break

  def __get_sensor_value(self):
    # Set 'Trigger' pin to HIGH
    GPIO.output(self.__pins[0], True)
    # Set 'Trigger' pin after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(self.__pins[0], False)
    
    start_time = time.time()
    stop_time = time.time()
    # Save start_time
    while GPIO.input(self.__pins[1]) == 0:
        start_time = time.time()
    # Save time of arrival
    while GPIO.input(self.__pins[1]) == 1:
        stop_time = time.time()
    # Time between start_time and time of arrival
    time_elapsed = stop_time - start_time
    # Multiply time_elapsed by speed of sound divided by two because sound traveled the distance to object and back.
    distance = time_elapsed * 17150

    return distance

class SensorManager:
  def __init__(self):
    self.__running = False

  def RunSensors(self, callback, read_speed = 1):
    def __sensor_process():
        GPIO.setmode(GPIO.BOARD)
        self.__sensors = [Sensor(SensorType.In), Sensor(SensorType.Out)]
        
        self.__running = True
        self.__sensors[0].BeginReading(callback, read_speed = read_speed)
        self.__sensors[1].BeginReading(callback, read_speed = read_speed)
        
    __sensor_process()

  def StopSensors(self):
    if self.__running:
      self.__running = False
      self.__sensors[0].StopReading()
      self.__sensors[1].StopReading()
      
      GPIO.cleanup()

  def PauseSensor(self, sensor_type):
    self.__sensors[sensor_type.value].PauseReading()

  def UnpauseSensor(self, sensor_type):
    self.__sensors[sensor_type.value].UnpauseReading()
    