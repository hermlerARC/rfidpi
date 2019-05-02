'''
RFID Logging Software

Description (reading_manager.py):
Uses Mercury API for Python to read tags from the RFID reader.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''
from multiprocessing import Process, Queue, Value
from ctypes import c_bool
import datetime, time
from sensors import *
from tag import *
from node_enums import Status

class Direction:
    def __init__(self, status, time_range):
        self.Status = status
        self.TimeRange = time_range

class TimeRange:
  def __init__(self, start_time, end_time, expansion = 0):
    if isinstance(start_time, datetime.datetime) and isinstance(end_time, datetime.datetime):
      self.StartTime = start_time - datetime.timedelta(seconds=expansion)
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
        lm = LaserManager()
        while True:
            print(lm.InLaser.Value)
            time.sleep(1)

    def BeginReading(self, callback, testing = False):
        if hasattr(callback, '__call__'):
            tag_queue = Queue(1)
            tag_queue.put([])
            
            with self.__running.get_lock():
                self.__running.value = True
            
            Process(target=self.__run_lasers, args=(tag_queue, self.__running)).start()
            Process(target=self.__run_sender, args=(tag_queue, self.__running, callback)).start()
            Process(target=self.__run_reader, args=(tag_queue, self.__running, testing)).start()
        else:
            raise ValueError('Must specify callback function')

    def StopReading(self):
        with self.__running.get_lock():
            self.__running.value = False

    def ReadOnce(self):
        tag_data = self.__reader.read()[0]
        return Tag(str(tag_data.epc, 'utf-8'), TagStatus.Unknown, tag_data.rssi)

    def __run_sender(self, tag_queue, run_val, callback):
        while True:
            running = False
            with run_val.get_lock(): running = run_val.value
            if not running: break
            
            curr_time = datetime.datetime.now()

            tags = tag_queue.get()
            for i in range(len(tags)-1, -1, -1):
                if (curr_time - tags[i].Timestamp).total_seconds() > self.__THRESHOLD_TIME or tags[i].Status != TagStatus.Unknown:
                    for j in range(i, -1, -1):
                        callback(tags[j])
                        tags.pop(j)
                        break
            tag_queue.put(tags)
            time.sleep(1)

    def __run_reader(self, tag_queue, run_val, testing):
        while True:
            running = False
            with run_val.get_lock(): running = run_val.value
            if not running: break

            tag_reads = self.__reader.read(2000)
            curr_time = datetime.datetime.now()

            tags = tag_queue.get()
            for tag_data in tag_reads:
                tags.append(Tag(tag_data.epc, TagStatus.Unknown, tag_data.rssi))
            tag_queue.put(tags)
            
            time.sleep(1)

    def __run_lasers(self, tag_queue, run_val):
        def update_tag_directions(time_range, status):
            time.sleep(1.5)
            tags = tag_queue.get()
            for i in range(len(tags)-1, -1, -1):
                if time_range.Contains(tags[i].Timestamp):
                    tags[i].Status = status
            tag_queue.put(tags)
        
        lm = LaserManager()
        while True:
            running = False
            with run_val.get_lock(): running = run_val.value
            if not running: break

            
            ts = datetime.datetime.now()
            
            if not lm.InLaser.Value and lm.OutLaser.Value:
                while (datetime.datetime.now() - ts).total_seconds() < 3:
                    if not lm.OutLaser.Value:
                        update_tag_directions(TimeRange(ts, datetime.datetime.now(), 2), TagStatus.Out)
                        time.sleep(0.5)
                        break
            if not lm.OutLaser.Value and lm.InLaser.Value:
                while (datetime.datetime.now() - ts).total_seconds() < 3:
                    if not lm.InLaser.Value:
                        update_tag_directions(TimeRange(ts, datetime.datetime.now(), 2), TagStatus.In)
                        time.sleep(0.5)
                        break