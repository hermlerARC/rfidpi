'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: May 4, 2019
'''
from multiprocessing import Process, Queue, Value
from ctypes import c_bool
import datetime, time
from sensors import *
from tag import *
from node_enums import Status

class TimeRange:
  def __init__(self, start_time, end_time, expansion = 0):
    if isinstance(start_time, datetime.datetime) and isinstance(end_time, datetime.datetime):
      self.StartTime = start_time + datetime.timedelta(seconds=-expansion)
      self.EndTime = end_time + datetime.timedelta(seconds=expansion)
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
  def __init__(self, reader):
    self.__THRESHOLD_TIME = 3

    self.__reader = reader
    self.__running = Value(c_bool, False)

  def __test_laser(self):
    """
    Temporary internal method of testing the lasers for their values.
    """


  def BeginReading(self, callback):
    if hasattr(callback, '__call__'):
      # Diagrams for how Reading Manager works can be seen in ../Diagrams/
      # The direction queue will hold the list of all directions logged by the lasers
      # The tag queue holds the list of all tags read by the RFID reader

      direction_queue = Queue(1)
      direction_queue.put([])
      tag_queue = Queue(1)
      tag_queue.put([])
      
      # Tells the new processes that the program is running
      with self.__running.get_lock():
        self.__running.value = True
      
      # Create and start processes for the laser scanning, RFID reader reading, and MQTT publishing.
      Process(target=self.__run_lasers, args=(direction_queue, self.__running)).start()
      Process(target=self.__run_sender, args=(tag_queue, direction_queue, self.__running, callback)).start()
      Process(target=self.__run_reader, args=(tag_queue, self.__running, testing)).start()
    else:
      raise ValueError('Must specify callback function')

  def StopReading(self):
    # Tells the processes to stop running and to exit
    with self.__running.get_lock():
      self.__running.value = False

  def ReadOnce(self):
    tag_data = self.__reader.read()[0]
    return Tag(str(tag_data.epc, 'utf-8'), TagStatus.Unknown, tag_data.rssi)

  def StartLaserTest(self, callback, timeout = 1):
    lm = LaserManager()

    with self.__running.get_lock():
      self.__running = True

    while True:
      running = False
      with self.__running.get_lock(): running = self.__running.value
      if not running: break

      callback([Laser.Type.Out, lm.OutLaser.Value])
      callback([Laser.Type.In, lm.InLaser.Value])
      time.sleep(timeout)

  def StartReaderTest(self, callback, timeout = 1):
    with self.__running.get_lock():
      self.__running = True

    while True:
      running = False
      with self.__running.get_lock(): running = self.__running.value
      if not running: break
      
      tag_data = self.__reader.read()
      for x in tag_data:
        callback(Tag(str(x.epc, 'utf-8'), TagStatus.Unknown, tag_data.rssi))
      time.sleep(timeout)

  def StopLaserTest(self): self.StopReading()

  def StopReaderTest(self): self.StopReading()

  def __run_sender(self, tag_queue, dir_queue, run_val, callback):
    """
    Syncs tags queue to direction queue and calls the callback with each updated tag.
    """

    wait_time = self.__THRESHOLD_TIME * 2
    while True:
      # Checks to see if node is running
      running = False
      with run_val.get_lock(): running = run_val.value
      if not running: break
      
      curr_time = datetime.datetime.now()

      tags = tag_queue.get()
      dirs = dir_queue.get()
      
      for x in dirs:
        for y in tags:
          # If the current tag was read within the time of a direction and sync it's direction.
          # See ../Diagrams for a visual explanation
          if x[0].Contains(y.Timestamp):
            y.Status = x[1]

      for y in [x for x in tags if x.Status != TagStatus.Unknown]: callback(y)
          
      tag_queue.put([])
      dir_queue.put([])
      
      time.sleep(wait_time)

  def __run_reader(self, tag_queue, run_val, testing):
    """
    Reads and processes tags read by RFID reader and places them into the tag queue
    """
    
    while True:
      # Checks to see if node is running
      running = False
      with run_val.get_lock(): running = run_val.value
      if not running: break

      # Reads for tags
      tag_reads = self.__reader.read(2000)
      curr_time = datetime.datetime.now()

      tags = tag_queue.get()
      # Pulls EPC and RSSI off the data from the Mercury API
      for tag_data in tag_reads:
          tags.append(Tag(tag_data.epc, TagStatus.Unknown, tag_data.rssi))
      tag_queue.put(tags)
      
      # Arbitrary sleep time. Can be removed
      time.sleep(1)

  def __run_lasers(self, dir_queue, run_val):
    def update_tag_directions(time_range, status):
      dirs = dir_queue.get() # Acquire access to the list of directions inside of dir_queue
      dirs.append([time_range, status]) # Add this new direction to the list
      dir_queue.put(dirs) # Put the list back into dir_queue
    
    # See sensors.py for LaserManager details
    lm = LaserManager()

    while True:
      # Checks to see if node is running
      running = False
      with run_val.get_lock(): running = run_val.value
      if not running: break
      ts = datetime.datetime.now()
      
      # The two following if-then blocks checks to see if there is an object in front of it and no object
      # in front of it's complement. If this is the case, wait to see if an object then passes by it's complement.
      # If an object passes by withing __THRESHOLD_TIME, then that implies that something has passed by both sensors
      # and has a momentum in the direction of the most recent laser reading. When this happens, this process will add this
      # direction and the time it took for an object to pass by both lasers (plus a padding) into the dir_queue by calling update_tag_directions()
      # See ../Diagrams/ for laser graphic

      if not lm.InLaser.Value and lm.OutLaser.Value:
        while (datetime.datetime.now() - ts).total_seconds() < self.__THRESHOLD_TIME:
          if not lm.OutLaser.Value:
            update_tag_directions(TimeRange(ts, datetime.datetime.now(), self.__THRESHOLD_TIME), TagStatus.Out)
            time.sleep(0.5)
            break
              
      if not lm.OutLaser.Value and lm.InLaser.Value:
        while (datetime.datetime.now() - ts).total_seconds() < self.__THRESHOLD_TIME:
          if not lm.InLaser.Value:
            update_tag_directions(TimeRange(ts, datetime.datetime.now(), self.__THRESHOLD_TIME), TagStatus.In)
            time.sleep(0.5)
            break