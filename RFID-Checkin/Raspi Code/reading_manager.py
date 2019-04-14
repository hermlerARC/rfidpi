'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

import threading, datetime, time
from sensors import *
from paho.mqtt import publish
import Tag

def reading_manager(pipe, reader):

  global tags
  global TIME_THRESHOLD
  global process_running
  global RUN_READER
  
  read(reader)
  
  while process_running:
      '''
      Wait for a read signal from the scanning manager.
      Message will give the time range of the tripped sensors.
      Increase the range by TIME_THRESHOLD.
      '''
      times = pipe.recv()
      times = [times[0] - datetime.timedelta(seconds=TIME_THRESHOLD/2), times[1] + datetime.timedelta(seconds=TIME_THRESHOLD/2)]
      adjusted_tags = []

      lock.acquire()
      if len(tags) > 0:  
          ranged_tags = list(filter(lambda x: x[2] > times[0] and x[2] < times[1], tags)) # Get all tags within the time range
          
          lock.release()
            
          # Discard any duplicate tag reads.
          for x in ranged_tags:
            if x[0] not in list(map(lambda y: y[0], adjusted_tags)):
              adjusted_tags.append(x)
      else:
          lock.release()
          
      pipe.send(adjusted_tags) # Release tags back over the pipe
      
  RUN_READER = False # Stops reading thread

class ReadingManager():
  def __init__(self, reader, threshold_distace = 150, threshold_time = 3):
    self.__reader = reader

    if not isinstance(threshold_distace, int) or threshold_distace < 1:
      print("Invalid threshold_distance argument: {}".format(threshold_distace))
      raise ValueError
    if not isinstance(threshold_time, int) or threshold_time < 1:
      print("Invalid threshold_time argument: {}".format(threshold_time))
      raise ValueError

    self.__threshold_distance = threshold_distace
    self.__threshold_time = threshold_time

    self.__sensor_readings = []
    self.__sensor_readings_lock = threading.Lock()
    
    self.__running = False

  def BeginReading(self, testing_callback = None, testing_threshold = 300):
    if self.__running:
      return ResponseCodes.READER_RUNNING

    self.__running = True

    if hasattr(testing_callback, '__call__') and isinstance(testing_callback, int) and testing_callback > 0:
      self.__reader.start_reading(testing_callback)
    else:
      self.__run_scanners()
      self.__reader.start_reading(self.__log_tag)

    return ResponseCodes.READER_RUNNING

  def StopReading(self):
    if not self.__running:
      return ResponseCodes.READER_STOPPED
    
    self.__running = False
    self.__in_sensor.StopReading()
    self.__out_sensor.StopReading()
    self.__sensor_readings.clear()
    self.__reader.stop_reading()

  def ReadOnce(self):
    tag_data = self.__reader.read()[0]
    return {
      'EPC' : str(tag_data.epc, 'utf-8')
    }

  def __log_tag(self, tag_data):
    curr_time = datetime.datetime.now()
    epc = str(tag_data,epc, 'utf-8')
    direction = self.__get_direction(curr_time)
    
    tag = Tag.Tag(epc, direction, tag_data.rssi)    
    client.publish('reader/{}/reading'.format(RASPI_ID), json.dumps(tag.to_json()), qos=1)

  def __get_direction(self, ctime):
    self.__sensor_readings_lock.acquire()

    while True and len(self.__sensor_readings) > 0:
      first_reading = self.__sensor_readings.pop()
      if (datetime.datetime.now() - curr_reading['Timestamp']).total_seconds() < self.__threshold_time:
        pass

  def __run_scanners(self):
    def receive_reading(sensor_type, value):
      if value <= self.__threshold_distance:
        self.__sensor_readings_lock.acquire()

        self.__sensor_readings.push({
          "Timestamp" : datetime.datetime.now(),
          "Sensor" : sensor_type
        })

        self.__sensor_readings_lock.release()

    self.__in_sensor = Sensor(SensorType.In_Sensor)
    self.__out_sensor = Sensor(SensorType.Out_Sensor)
    
    self.__in_sensor.BeginReading(callback=receive_reading)
    self.__out_sensor.BeginReading(callback=receive_reading)
