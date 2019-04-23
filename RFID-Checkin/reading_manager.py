'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

import threading, datetime
from sensors import *
from tag import *
from node_enums import Status

class Direction:
  def __init__(self, time_range, tag_status):
    self.TimeRange = time_range
    self.TagStatus = tag_status
    
  def __str__(self):
      return "{}\t{}".format(self.TimeRange, self.TagStatus)

class TimeRange:
  def __init__(self, start_time, end_time):
    if isinstance(start_time, datetime.datetime) and isinstance(end_time, datetime.datetime):
      self.StartTime = start_time
      self.EndTime = end_time
    else:
      raise ValueError('start_time and end_time must be an instance of datetime')

  def Contains(self, test_time):
    if isinstance(test_time, datetime.datetime):
      return self.StartTime <= test_time and test_time <= self.EndTime
    elif isinstance(test_time, TimeRange):
      return self.StartTime <= test_time.StartTime and test_time.EndTime <= self.EndTime

  def Duration(self):
    return (self.EndTime - self.StartTime)

  def __str__(self):
    return "[{},{}]".format(self.StartTime, self.EndTime)

class ReadingManager():
  def __init__(self, reader, sensor_manager):
    self.__THRESHOLD_TIME = 3

    self.__reader = reader
    self.__sensor_manager = sensor_manager
    self.__running = False

    self.__directions = []
    self.__directions_lock = threading.Lock()
    self.__sensor_reading = None

  def BeginReading(self, callback, sensor_threshold = 300, testing = False):
    if hasattr(callback, '__call__'):
      if isinstance(sensor_threshold, int) and sensor_threshold > 0:
        self.__status = Status.RUNNING_READER_TEST if testing else Status.LOGGING

        self.__sensor_threshold = sensor_threshold

        self.__running = True
        self.__run_reader(callback, testing)
        self.__run_sensors()
      else:
        raise ValueError("Sensor threshold must be an int that's greater than 0")
    else:
      raise ValueError('Must specify callback function')

  def StopReading(self):
    self.__running = False
    self.__sensor_manager.StopSensors()
    self.__directions_lock.acquire()
    self.__directions.clear()
    self.__directions_lock.release()
    self.__reader.stop_reading()

  def ReadOnce(self):
    tag_data = self.__reader.read()[0]
    return Tag(str(tag_data.epc, 'utf-8'), TagStatus.Unknown, tag_data.rssi)

  def __run_reader(self, callback, testing):
    def start_reading():
      while self.__running:
        tag_reads = self.__reader.read()
        curr_time = datetime.datetime.now()
        for tag_data in tag_reads:
          direction = TagStatus.Unknown
      
          if not testing:
            direction = self.__get_direction(curr_time)
      
          callback(Tag(tag_data.epc, direction, tag_data.rssi))
          
    threading.Thread(target=start_reading, daemon=True).start()
  def __get_direction(self, search_time):
    tag_status = TagStatus.Unknown
    
    self.__directions_lock.acquire()
    while len(self.__directions) > 0:
      curr_dir = self.__directions.pop(0)

      for x in self.__directions:
          print("dir: ", x)
          
      print(search_time)
      if curr_dir.TimeRange.Contains(search_time):
        tag_status = curr_dir.TagStatus
    self.__directions_lock.release()
    
    return tag_status

  def __run_sensors(self):
    def receive_reading(sensor_reading):
      if sensor_reading.Reading <= self.__sensor_threshold:
        if self.__sensor_reading == None:
          self.__sensor_manager.PauseSensor(sensor_reading.SensorType)
          self.__sensor_reading = sensor_reading
        elif (datetime.datetime.now() - self.__sensor_reading.Timestamp).total_seconds() > self.__THRESHOLD_TIME:
          self.__sensor_manager.UnpauseSensor(sensor_reading.SensorType.Opposite)
          self.__sensor_manager.PauseSensor(sensor_reading.SensorType)
          self.__sensor_reading = sensor_reading
        else:
          time_of_walk = TimeRange(self.__sensor_reading.Timestamp, sensor_reading.Timestamp)

          self.__directions_lock.acquire()
          self.__directions = self.__directions[-5:] # Remove old data
          direction = Direction(time_of_walk, sensor_reading.SensorType)
          self.__directions.append(direction)
          self.__directions_lock.release()

          self.__sensor_manager.UnpauseSensor(sensor_reading.SensorType.Opposite)
    self.__sensor_manager.RunSensors(receive_reading)