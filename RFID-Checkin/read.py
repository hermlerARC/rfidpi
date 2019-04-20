'''
RFID Logging Software

Description (read.py): 
Main script to run the Raspberry PI that handles creating and terminating the 
reporting and scanning processes. Receives calls from UI Client to read, read once, and stop reading.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 21, 2019
'''

from paho.mqtt import client as mqtt
from reading_manager import ReadingManager
from sensors import SensorManager
from node_enums import *
import pickle, mercury, datetime

# Unique ID to differentiate between different systems that are connected to the UI Client
RASPI_ID = 'UPOGDU'
LOG_FILE = "System Logs/{}.txt" # {} Are replaced by a datetime value in print_out()
DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'
READER_PATH = "tmr:///dev/ttyUSB"

def connect_to_reader(path = READER_PATH, max_port = 10):
  """
  Configure ThingMagic RFID Reader.

  Args:
    max_port: int, attempts to connect to the path[0-max_port]. For example, tmr:///dev/ttyUSB4

  Returns: 
    [response_codes.Response_Codes, mercury.Reader, str]
  """

  conn_port = 0
  reader = None

  while conn_port <= max_port:
    try:
      reader = mercury.Reader("{}{}".format(path, conn_port))
      reader.set_region('NA')

      return [reader, "{}{}".format(path, conn_port)]
    except:
      pass

  return [reader, ""]

class ManagerWrapper:
  def __init__(self, reader):
    self.__sensor_man = SensorManager()
    self.__print_out("created sensor manager")

    self.__reading_man = ReadingManager(reader, self.__sensor_man)
    self.__print_out("created reading manager")
    self.__status = Status.ONLINE

    # Attempt to connect to MQTT
    self.__client = mqtt.Client(transport='websockets')  # Connect with websockets
    self.__client.on_connect = __client_connected
    self.__client.on_message = __client_messaged
    self.__client.connect('broker.hivemq.com', port=8000)

    try:
      self.__client.loop_forever()
    except KeyboardInterrupt:
      self.Shutdown()

  #region Manager Handling
  def BeginLogging(self, callback):
    self.__check_availability()

    self.__reading_man.BeginReading(callback=callback)
    self.__update_status(Status.LOGGING)
    self.__print_out('reading manager running in log mode')

  def StopLogging(self):
    if self.__status == Status.LOGGING:
      self.__reading_man.StopReading()
      self.__update_status(Status.ONLINE)
      self.__print_out('stopped reading manager logging')

  def BeginTesting(self, callback):
    self.__check_availability()

    self.__reading_man.BeginReading(callback=callback, testing=True)
    self.__update_status(Status.RUNNING_READER_TEST)
    self.__print_out('reading manager running in test mode')

  def StopTesting(self):
    if self.__status == Status.RUNNING_READER_TEST:
      self.__reading_man.StopReading()
      self.__update_status(Status.ONLINE)
      self.__print_out('stopped reading manager testing')

  def ReadOnce(self, callback):
    self.__check_availability()

    self.__update_status(Status.REQUESTING_TAG)
    self.__print_out('requesting single tag')
    callback(self.__reading_man.ReadOnce())
    self.__update_status(Status.ONLINE)

  def TestSensors(self, callback):
    self.__check_availability()

    self.__sensor_man.RunSensors(callback=callback)
    self.__update_status(Status.RUNNING_SENSOR_TEST)
    self.__print_out('beginning sensor test')

  def StopSensors(self):
    if self.__status == Status.RUNNING_SENSOR_TEST:
      self.__sensor_man.StopSensors()
      self.__update_status(Status.ONLINE)
      self.__print_out('stopping sensor test')
  #endregion

  #region Client Handling
  def __client_messaged(self, client, data, msg):
    command = pickle.loads(msg.payload)
    self.__send_message(client, Topic.NODE_RESPONSE, repr(command)) # Reply to the sender to let it know we've received the message
    self.__print_out("received message '{}'".format(command))

    try:
      if command == Command.START_LOGGING:
        self.BeginLogging(callback=self.__log_tag)
      elif command == Command.STOP_LOGGING:
        self.StopLogging()
      elif command == Command.READ_ONCE:
        self.ReadOnce(callback=self.__log_tag)
      elif command == Command.BEGIN_SENSOR_TEST:
        self.TestSensors(callback=self.__log_sensor_reading)
      elif command == Command.STOP_SENSOR_TEST:
        self.StopSensors()
      elif command == Command.BEGIN_READER_TEST:
        self.BeginTesting(callback=self.__log_tag)
      elif command == Command.STOP_READER_TEST:
        self.StopTesting()
      elif command == Command.CHECK_STATUS:
        self.__post_status()
    except NodeBusy as error:
      self.__post_error(command, error)

  def __client_connected(self, client, data, flags, rc):
    client.subscribe('reader/{}/{}'.format(RASPI_ID, NodeTopic.COMMANDS), 1)
    self.__print_out("connected to MQTT client on 'reader/{}/{}'".format(RASPI_ID, Topic.COMMANDS))

  def __send_message(self, topic, message):
    if isinstance(topic, Topic):
      message_obj = {'TIMESTAMP' : datetime.datetime.now(), 'ID' : RASPI_ID, 'BODY' : message}
      self.__client.publish('reader/{}/{}'.format(RASPI_ID, topic.value), pickle.dumps(message_obj), qos=1)
    else:
      raise ValueError("'topic' argument must be an instance of Topic")
  #endregion

  def Shutdown(self):
    self.StopLogging()
    self.StopTesting()
    self.StopSensors()

    return self.Status

  @property
  def Status(self):
    return self.__status

  def __post_status(self):
    self.__send_message(Topic.NODE_STATUS, self.Status)

  def __post_error(self, trigger, error):
    """
    Posts an error code and the message, if any, that caused it to the ERRORS topic.
    """
    error_obj = {"TRIGGER_COMMAND" : trigger, "ERROR_MESSAGE" : error}
    self.__send_message(Topic.ERROR_CODES, error_obj)
    self.__print_out("{} caused error '{}': {}".format(trigger, error.Error, error.Message))

  def __check_availability(self):
    if self.__status == Status.LOGGING:
      raise NodeBusy(NodeError.NODE_BUSY_LOGGING)
    elif self.__status == Status.REQUESTING_TAG:
      raise NodeBusy(NodeError.NODE_BUSY_REQUESTING_TAG)
    elif self.__status == Status.RUNNING_READER_TEST:
      raise NodeBusy(NodeError.NODE_BUSY_TESTING_READER)
    elif self.__status == Status.RUNNING_SENSOR_TEST:
      raise NodeBusy(NodeError.NODE_BUSY_TESTING_SENSORS)

  def __print_out(self, msg):
    """
    Prints data to the LOG_FILE and out to the screen.
    """
    curr_time = datetime.datetime.now()
    ft_msg = "{}\t{}".format(curr_time.strftime(DATETIME_FORMAT), msg)

    print(ft_msg)
    with open(LOG_FILE.format(curr_time.strftime('%m-%d-%Y')), 'a') as LF:
      LF.write(ft_msg)

  def __log_tag(self, tag):
    self.__send_message(Topic.TAG_READINGS, tag.__dict__)
    self.__print_out('read tag: {}'.format(tag.__dict__))

  def __log_sensor_reading(self, sensor_reading):
    self.__send_message(Topic.SENSOR_READINGS, sensor_reading.__dict__)
    self.__print_out('read sensor value: {}'.format(sensor_reading.__dict__))

  def __update_status(self, status):
    if isinstance(status, Status):
      self.__status = status
      self.__post_status()

      self.__print_out("current node status: {}".format(self.Status.value))

if __name__ == '__main__':
  # Attempt to connect to reader
  reader, conn_path = connect_to_reader()
  if conn_path != "":
    print_out("connected to reader on '{}'".format(conn_path))
  else:
    raise ReaderUnreachable
    exit(1)

  node_manager = ManagerWrapper(reader)