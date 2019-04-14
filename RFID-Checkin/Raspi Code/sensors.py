'''
RFID Logging Software

Description (sensors.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Source code: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/

Edited on: March 21, 2019
'''

import RPi.GPIO as GPIO
import time, threading, enum, read
from response_codes import ResponseCodes

class SensorType(enum.Enum):
  In_Sensor = 0
  Out_Sensor = 1

  def __str__(self):
    return self.name

class SensorStatus(enum.Enum):
  Running = 0
  Paused = 1
  Stopped = 2

class Sensor:
  def __init__(self, sensor_type):
    IN_PINS = [18,23]
    OUT_PINS = [25,24]

    self.__sensor_type = sensor_type
    self.__status = SensorStatus.Stopped
    self.__pins = IN_PINS if self.__sensor_type == SensorType.In_Sensor else OUT_PINS

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self.__pins[0], GPIO.OUT)
    GPIO.setup(self.__pins[1], GPIO.IN)

  def BeginReading(self, read_speed = 1, callback = None):
    if self.__status == SensorStatus.Running:
      return ResponseCodes.SENSOR_RUNNING
    elif self.__status == SensorStatus.Paused:
      return ResponseCodes.SENSOR_PAUSED

    if isinstance(read_speed, int) and read_speed > 0:
      self.__read_speed = read_speed
      
      self.__reading_callback = callback
      self.__status = SensorStatus.Running
      
      run_thread = threading.Thread(target=self.__run)
      run_thread.start()

      return ResponseCodes.SENSOR_RUNNING
    else:
      print("Invalid read_speed argument: {}".format(read_speed))
      raise ValueError

  def StopReading(self):
    if self.__status == SensorStatus.Stopped:
      return ResponseCodes.SENSOR_STOPPED
    elif self.__status == SensorStatus.Stopped or self.__status == SensorStatus.Paused:
      self.__status = SensorStatus.Stopped
      return ResponseCodes.SENSOR_STOPPED

  def PauseReading(self):
    if self.__status == SensorStatus.Paused:
      return ResponseCodes.SENSOR_PAUSED
    elif self.__status == SensorStatus.Running:
      self.__status = SensorStatus.Paused
      return ResponseCodes.SENSOR_PAUSED
    elif self.__status == SensorStatus.Stopped:
      return ResponseCodes.SENSOR_STOPPED

  def ContinueReading(self):
    if self.__status == SensorStatus.Paused:
      self.__status = SensorStatus.Running
      return ResponseCodes.SENSOR_RUNNING
    elif self.__status == SensorStatus.Running:
      return ResponseCodes.SENSOR_RUNNING
    elif self.__status == SensorStatus.Stopped:
      return ResponseCodes.SENSOR_STOPPED

  def Status(self):
    return self.__running

  def __run(self, callback):
    while True:
      if self.__running == SensorStatus.Running:
        if hasattr(self.__reading_callback, '__call__'):
          callback(self.__sensor_type, self.__get_sensor_value())
          time.sleep(1/ self.__read_speed)
      elif self.__running == SensorStatus.Paused:
        continue
      elif self.__running == SensorStatus.Stopped:
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
