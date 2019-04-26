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
    def __init__(self, status, time_range):
        self.Status = status
        self.TimeRange = time_range

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
  def __init__(self, reader):
    self.__THRESHOLD_TIME = 3

    self.__reader = reader
    self.__running = False

    self.__tag_stream = []
    self.__tag_stream_lock = threading.Lock()

    def BeginReading(self, callback, testing = False):
        if hasattr(callback, '__call__'):
            self.__running = True
            threading.Thread(target=self.__run_lasers).start()
            threading.Thread(target=self.__run_sender, args=(callback,)).start()
            threading.Thread(target=self.__run_reader, args=(testing,)).start()
        else:
            raise ValueError('Must specify callback function')

    def StopReading(self):
        self.__running = False
        self.__tag_stream_lock.acquire()
        self.__tag_stream.clear()
        self.__tag_stream_lock.release()

    def ReadOnce(self):
        tag_data = self.__reader.read()[0]
        return Tag(str(tag_data.epc, 'utf-8'), TagStatus.Unknown, tag_data.rssi)

    def __run_sender(self, callback):
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

    def __run_reader(self, testing):
        while self.__running:
            tag_reads = self.__reader.read(2000)
            curr_time = datetime.datetime.now()

        for tag_data in tag_reads:
            self.__tag_stream_lock.acquire()
            self.__tag_stream.append(Tag(tag_data.epc, TagStatus.Unknown, tag_data.rssi))
            self.__tag_stream_lock.release()

    def __run_lasers(self):
        lm = LaserManager()
        while self.__running:
            ts = datetime.datetime.now()
    
            if not lm.InLaser.Value and lm.OutLaser.Value:
                while (datetime.datetime.now() - ts).total_seconds() < 3:
                    if not lm.OutLaser.Value:
                        print('{} heading {}'.format(datetime.datetime.now(), 'out'))
                    
##                    self.__tag_stream_lock.acquire()
##                    for i in range(len(self.__tag_stream)-1, -1, -1):
##                      if time_of_walk.Contains(self.__tag_stream[i].Timestamp):
##                        self.__tag_stream[i].Status = TagStatus.Out
##                      else:
##                        break
##                    self.__tag_stream_lock.release()
                    
                        time.sleep(0.5)
                        break
                    
            if not lm.OutLaser.Value and lm.InLaser.Value:
                while (datetime.datetime.now() - ts).total_seconds() < 3:
                    if not lm.InLaser.Value:
                        print('{} heading {}'.format(datetime.datetime.now(), 'in'))
                        
    ##                    self.__tag_stream_lock.acquire()
    ##                    for i in range(len(self.__tag_stream)-1, -1, -1):
    ##                      if time_of_walk.Contains(self.__tag_stream[i].Timestamp):
    ##                        self.__tag_stream[i].Status = TagStatus.Out
    ##                      else:
    ##                        break
    ##                    self.__tag_stream_lock.release()
                        
                        time.sleep(0.5)
                        break
        asd
