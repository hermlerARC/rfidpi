'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

import threading, datetime, Tag, response_codes
from sensors import *

class Direction:
  def __init__(self, time_range, tag_status):
    self.TimeRange = time_range
    self.TagStatus = tag_status

class TimeRange:
  def __init__(self, start_time, end_time):
    if isinstance(start_time, datetime.datetime) and isinstance(end_time, datetime.datetime):
      self.StartTime = start_time
      self.EndTime = end_time
    else:
      print('start_time and end_time must be an instance of datetime')
      raise ValueError

  def Contains(self, test_time):
    if isinstance(test_time, datetime):
      return self.StartTime <= test_time and test_time <= self.EndTime
    elif isinstance(test_time, TimeRange):
      return self.StartTime <= test_time.StartTime and test_time.EndTime <= self.EndTime

  def Duration(self):
    return (self.EndTime - self.StartTime)

class ReadingManager():
  def __init__(self, reader, sensor_manager):
    self.__THRESHOLD_TIME = 3

    self.__reader = reader

    self.__directions = []
    self.__directions_lock = threading.Lock()
    self.__sensor_reading = None

    self.__running = False

  def BeginReading(self, callback = None, sensor_threshold = 300, testing = False):
    def __log_tag(tag_data):
      curr_time = datetime.datetime.now()
      direction = self.__get_direction(curr_time) if testing else Tag.TagStatus.Unknown
      
      tag = Tag.Tag(tag_data.epc, direction, tag_data.rssi)
      callback(tag)

    if self.__running:
      return ResponseCodes.NODE_RUNNING

    self.__running = True

    if hasattr(callback, '__call__'):
      if isinstance(sensor_threshold, int) and sensor_threshold > 0:
        self.__sensor_threshold = sensor_threshold

        self.__run_sensors()
        self.__reader.start_reading(__log_tag)

        return ResponseCodes.NODE_RUNNING
      else:
        print("Sensor threshold must be an int that's greater than 0")
        return ResponseCodes.NODE_STOPPED
    else:
      print('Must specify callback function')
      return ResponseCodes.NODE_STOPPED


  def StopReading(self):
    if not self.__running:
      return ResponseCodes.NODE_STOPPED
    
    self.__running = False
    self.__sensor_manager.StopSensors()
    self.__readings_container.Clear()
    self.__reader.stop_reading()

    return ResponseCodes.NODE_STOPPED

  def ReadOnce(self):
    if self.__running:
      print('Cannot read while this instance of Reading Manager is active')
      raise RuntimeError

    tag_data = self.__reader.read()[0]
    tag = Tag.Tag(str(tag_data.epc, 'utf-8'), Tag.TagStatus.Unknown, tag_data.rssi)

    return tag

  def IsRunning(self):
    return ResponseCodes.NODE_RUNNING if self.__running else ResponseCodes.NODE_STOPPED

  def __get_direction(self, search_time):
    self.__directions_lock.acquire()
    
    tag_status = Tag.TagStatus.Unknown

    for direction in self.__readings_container.Directions:
      if direction.TimeRange.Contains(search_time):
        tag_status = direction.Direction
        break
    
    self.__directions_lock.release()
    
    return tag_status

  def __run_sensors(self):
    def receive_reading(sensor_reading):
      if sensor_reading.Reading <= self.__sensor_threshold:
        if self.__sensor_reading == None:
          self.__sensor_manager.PauseSensor(sensor_reading.SensorType)
          self.__sensor_reading = sensor_reading
        elif (datetime.datetime.now() - self.__sensor_reading.Timestamp).total_seconds() > self.__THRESHOLD_TIME:
          self.__sensor_manager.UnpauseSensor(sensor_reading.SensorType.Opposite())
          self.__sensor_manager.PauseSensor(sensor_reading.SensorType)
          self.__sensor_reading = sensor_reading
        else:
          time_of_walk = TimeRange(self.__sensor_reading.Timestamp, sensor_reading.Timestamp)

          self.__directions_lock.acquire()
          self.__directions.append(Direction(time_of_walk, sensor_reading.SensorType))
          self.__directions_lock.release()

          self.__sensor_manager.UnpauseSensor(sensor_reading.SensorType.Opposite())

    self.__sensor_manager.RunSensors(callback=receive_reading)
