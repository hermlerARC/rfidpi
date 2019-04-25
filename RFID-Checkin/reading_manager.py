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

class ReadingManager:
  def __init__(self, reader, sensor_manager):
    self.__THRESHOLD_TIME = 3

    self.__reader = reader
    self.__sensor_manager = sensor_manager
    self.__running = False

    self.__tag_stream = []
    self.__tag_stream_lock = threading.Lock()
    self.__sensor_reading = None

  def BeginReading(self, callback, sensor_threshold = 300, testing = False):
    if hasattr(callback, '__call__'):
      if isinstance(sensor_threshold, int) and sensor_threshold > 0:
        self.__sensor_threshold = sensor_threshold

        self.__running = True
        self.__run_sender(callback)
        print('setup sender')
        self.__run_reader(testing)
        print('setup reader')
        self.__run_sensors()
        print('setup sensors')
      else:
        raise ValueError("Sensor threshold must be an int that's greater than 0")
    else:
      raise ValueError('Must specify callback function')

  def StopReading(self):
    self.__running = False
    self.__sensor_manager.StopSensors()
    self.__tag_stream_lock.acquire()
    self.__tag_stream.clear()
    self.__tag_stream_lock.release()

  def ReadOnce(self):
    tag_data = self.__reader.read()[0]
    return Tag(str(tag_data.epc, 'utf-8'), TagStatus.Unknown, tag_data.rssi)

  def __run_sender(self, callback):
    def send_thread():
      while self.__running:
        curr_time = datetime.datetime.now()

        self.__tag_stream_lock.acquire()
        for i in range(len(self.__tag_stream)-1, -1, -1):
          if (curr_time - self.__tag_stream[i].Timestamp).total_seconds() > self.__THRESHOLD_TIME or self.__tag_stream[i].Status != TagStatus.Unknown:
            for j in range(i, -1, -1):
              callback(self.__tag_stream[j])
              self.__tag_stream.pop(j)
            break
        self.__tag_stream_lock.release()
        time.sleep(1)

    threading.Thread(target=send_thread).start()

  def __run_reader(self, testing):
    def start_reading():
      while self.__running:
        tag_reads = self.__reader.read()
        curr_time = datetime.datetime.now()
        for tag_data in tag_reads:
          self.__tag_stream_lock.acquire()
          self.__tag_stream.append(Tag(tag_data.epc, TagStatus.Unknown, tag_data.rssi))
          self.__tag_stream_lock.release()
          
    threading.Thread(target=start_reading).start()

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

          self.__tag_stream_lock.acquire()
          for i in range(len(self.__tag_stream)-1, -1, -1):
            if time_of_walk.Contains(self.__tag_stream[i].Timestamp):
              self.__tag_stream[i].Status = sensor_reading.SensorType
          self.__tag_stream_lock.release()

          self.__sensor_manager.UnpauseSensor(sensor_reading.SensorType.Opposite)
    self.__sensor_manager.RunSensors(receive_reading)