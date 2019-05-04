'''
RFID Logging Software

Description (read.py): 
Main script to run the Raspberry PI that acts as a manager of the reading manager.
Receives commands from the MQTT connection. 

Contributors:
Dom Stepek

To read more about Mercury API for Python, go to: https://github.com/gotthardp/python-mercuryapi
To read more about Paho MQTT for Python, go to: https://pypi.org/project/paho-mqtt/
Edited on: May 4, 2019
'''

from paho.mqtt import publish, client as mqtt
from reading_manager import ReadingManager
from sensors import LaserManager
from node_enums import *
import pickle, mercury, datetime, pathlib, time
import RPi.GPIO as GPIO

# Unique ID to differentiate between different systems that are connected to handler.py
RASPI_ID = 'UPOGDU'
LOG_FILE = "System Logs/{}.txt" # {} is replaced by a datetime value in print_out()
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
    except: conn_port += 1

  return [reader, ""]

class ManagerWrapper:
  def __init__(self, reader):
    self.__print_out("connected to reader on '{}'".format(conn_path))

    self.__reading_man = ReadingManager(reader)
    self.__print_out("created reading manager")
    self.__status = Status.ONLINE

    # Attempt to connect to MQTT

    # Connect with websockets. Eventually, if the front end is moved to a private server, this can be replaced
    # with tcp. This isn't currently possible as American River College's WiFi has a firewall preventing this
    # connection type. Additionally, a more secure way of sending data, if necessary, is to connect with a client ID
    # that is recognized by the nodes.
    self.__client = mqtt.Client(transport='websockets')  # Connect with websockets
    self.__client.on_connect = self.__client_connected
    self.__client.on_message = self.__client_messaged
    self.__client.connect('broker.hivemq.com', port=8000)

    try: self.__client.loop_forever()
    except (KeyboardInterrupt, SystemExit): self.Shutdown()

  @property
  def Status(self):
    return self.__status
      
  def BeginLogging(self, callback):
    self.__check_availability()
    self.__reading_man.BeginReading(callback)
    self.__update_status(Status.LOGGING)

  def StopLogging(self):
    if self.__status == Status.LOGGING:
      self.__reading_man.StopReading()
      self.__update_status(Status.ONLINE)
 
  def ReadOnce(self, callback):
    self.__check_availability()

    self.__update_status(Status.REQUESTING_TAG)
    callback(self.__reading_man.ReadOnce())
    self.__update_status(Status.ONLINE)

  def BeginTesting(self, callback):
    self.__check_availability()
    
    self.__reading_man.StartReaderTest(callback)
    self.__update_status(Status.RUNNING_READER_TEST)

  def StopTesting(self):
    if self.__status == Status.RUNNING_READER_TEST:
      self.__reading_man.StopReaderTest()
      self.__update_status(Status.ONLINE)

  def TestLasers(self, callback):
    self.__check_availability()

    self.__reading_man.TestLasers(callback=callback)
    self.__update_status(Status.RUNNING_SENSOR_TEST)

  def StopLasers(self):
    if self.__status == Status.RUNNING_SENSOR_TEST:
      self.__reading_man.StopLaserTest()
      self.__update_status(Status.ONLINE)

  def Shutdown(self):
    self.StopLogging()
    self.StopTesting()
    self.StopLasers()
    
    self.__print_out('stopped all activity')
    
    self.SendSystemLogs()
    self.__send_message(Topic.NODE_STATUS, Status.OFFLINE)

    self.__print_out('sent logs to server')
    self.__print_out('shutting down node {}'.format(RASPI_ID))
           
    return self.Status

  def SendSystemLogs(self):
    log_data = ""
    file_name = LOG_FILE.format(datetime.datetime.now().strftime('%m-%d-%Y'))
    
    with open(file_name, 'r') as LF:
      log_data = LF.read()
      
    self.__send_message(Topic.NODE_LOG, { 'Name' : file_name.split(sep='/')[1], 'Logs' : log_data })

  def __client_messaged(self, client, data, msg):
    command = pickle.loads(msg.payload)
    self.__send_message(Topic.NODE_RESPONSE, repr(command)) # Reply to the sender to let it know we've received the message
    self.__print_out("received message '{}'".format(command))
    
    try:
      if command == Command.START_LOGGING:
        self.BeginLogging(self.__log_tag)
      elif command == Command.STOP_LOGGING:
        self.StopLogging()
      elif command == Command.READ_ONCE:
        self.ReadOnce(callback=self.__log_tag)
      elif command == Command.BEGIN_SENSOR_TEST:
        self.TestLasers(callback=self.__log_sensor_reading)
      elif command == Command.STOP_SENSOR_TEST:
        self.StopLasers()
      elif command == Command.BEGIN_READER_TEST:
        self.BeginTesting(self.__log_tag)
      elif command == Command.STOP_READER_TEST:
        self.StopTesting()
      elif command == Command.CHECK_STATUS:
        self.__post_status()
      elif command == Command.GET_LOGS:
        self.SendSystemLogs()
    except NodeBusy as error:
      self.__post_error(command, error)

  def __client_connected(self, client, data, flags, rc):
    client.subscribe('reader/{}/{}'.format(RASPI_ID, Topic.COMMANDS), 1)
    self.__print_out("connected to MQTT client on 'reader/{}/{}'".format(RASPI_ID, Topic.COMMANDS))

  def __send_message(self, topic, message):
    if isinstance(topic, Topic):
      message_obj = {'TIMESTAMP' : datetime.datetime.now(), 'ID' : RASPI_ID, 'BODY' : message}
      publish.single('reader/{}/{}'.format(RASPI_ID, topic.value), payload=pickle.dumps(message_obj), qos=1, hostname="broker.mqttdashboard.com", port=8000, transport="websockets")
    else:
      raise ValueError("'topic' argument must be an instance of Topic")

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
    """
    Checks to see if the node is available to change status that is not online or offline.
    """

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
    directory = LOG_FILE.split(sep='/')[0] + '/'
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE.format(curr_time.strftime('%m-%d-%Y')), 'a') as LF:
      LF.write(ft_msg + '\n')

  def __log_tag(self, tag):
    self.__send_message(Topic.TAG_READINGS, tag.__dict__)
    self.__print_out('read tag: {}'.format(tag.__dict__))

  def __log_sensor_reading(self, laser_reading):
    self.__send_message(Topic.SENSOR_READINGS, laser_reading)
    self.__print_out('read sensor value: {}'.format(sensor_reading))

  def __update_status(self, status):
    if isinstance(status, Status):
      self.__status = status
      self.__post_status()

      self.__print_out("current node status: {}".format(self.Status.value))

if __name__ == '__main__':
  # Attempt to connect to reader
  reader, conn_path = connect_to_reader()

  if conn_path == "":
    raise ReaderUnreachable
    exit(1)

  node_manager = ManagerWrapper(reader)