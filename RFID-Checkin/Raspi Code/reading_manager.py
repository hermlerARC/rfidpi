'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

import threading, datetime, Tag
from sensors import *

class ReadingsContainer:
  def __init__(self, timeout):
    self.Timeout = timeout

    self.InReads = []
    self.OutReads = []
    self.Directions = []

  def AddReading(self, sensor_reading):
    self.__clear_garbage_reads()

    if sensor_reading.SensorType == SensorType.In:
      if len(self.OutReads) > 0:
        self.Directions.append(Direction(TimeRange(self.OutReads[0].Timestamp, sensor_reading.Timestamp), Tag.TagStatus.In))
        self.OutReads.clear()
      else:
        self.InReads.append(sensor_reading)
    elif sensor_reading.SensorType == SensorType.Out:
      if len(self.InReads) > 0:
        self.Directions.append(Direction(TimeRange(self.InReads[0].Timestamp, sensor_reading.Timestamp), Tag.TagStatus.Out))
        self.InReads.clear()
      else:
        self.OutReads.append(sensor_reading)

  def Clear(self):
    self.InReads.clear()
    self.OutReads.clear()
    self.Directions.clear()

  def __clear_garbage_reads(self):
    for sensor_reading in self.InReads:
      if (datetime.datetime.now() - sensor_reading.Timestamp).total_seconds() > self.Timeout:
        self.InReads.remove(sensor_reading)

    for sensor_reading in self.OutReads:
      if (datetime.datetime.now() - sensor_reading.Timestamp).total_seconds() > self.Timeout:
        self.OutReads.remove(sensor_reading)

    for direction in self.Directions:
      if (datetime.datetime.now() - direction.TimeRange.EndTime).total_seconds() > self.Timeout:
        self.Directions.remove(direction)

class Direction:
  def __init__(self, time_range, direction):
    self.TimeRange = time_range
    self.Direction = direction

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

class ReadingManager():
  def __init__(self, reader, sensor_manager):
    self.__THRESHOLD_TIME = 3

    self.__reader = reader

    self.__sensor_manager = sensor_manager
    self.__readings_container = ReadingsContainer(self.__THRESHOLD_TIME)
    self.__readings_container_lock = threading.Lock()
    
    self.__running = False

  def BeginReading(self, callback = None, sensor_threshold = 300, testing = False):
    def __log_tag(tag_data):
      curr_time = datetime.datetime.now()
      direction = self.__get_direction(curr_time) if testing else Tag.TagStatus.Unknown
      
      tag = Tag.Tag(tag_data.epc, direction, tag_data.rssi)
      callback(tag)

    if self.__running:
      print('This instance of ReadingManager is already running')
      raise RuntimeError

    self.__running = True

    if hasattr(callback, '__call__'):
      if isinstance(sensor_threshold, int) and sensor_threshold > 0:
        self.__sensor_threshold = sensor_threshold

        self.__run_sensors()
        self.__reader.start_reading(__log_tag)

        return ResponseCodes.NODE_RUNNING
      else:
        print("Sensor threshold must be an int that's greater than 0")
        raise ValueError
        return ResponseCodes.NODE_STOPPED
    else:
      print('Must specify callback function')
      raise ValueError
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

  def __get_direction(self, ctime):
    self.__readings_container_lock.acquire()
    
    tag_status = Tag.TagStatus.Unknown

    for direction in self.__readings_container.Directions:
      if (direction.TimeRange.Contains(ctime)):
        tag_status = direction.Direction
        break
    
    self.__readings_container_lock.release()
    
    return tag_status

  def __run_sensors(self):
    def receive_reading(sensor_reading):
      if value <= self.__sensor_threshold:
        self.__sensor_readings_lock.acquire()
        self.__readings_container.AddReading(sensor_reading)
        self.__sensor_readings_lock.release()

    self.__sensor_manager.RunSensors(callback=receive_reading)
