import enum, threading, datetime
from paho.mqtt import client

class NodeStatus(enum.Enum):
  ONLINE = "online"
  OFFLINE = "offline"

  LOGGING = "logging"
  STOPPED = "stopped"

  RUNNING_SENSOR_TEST = "running sensor test"
  RUNNING_READER_TEST = "running reader test"

class NodeCommand(enum.Enum):
  START_LOGGING = "start_logging"
  STOP_LOGGING = "stop_logging"
  READ_ONCE = "read_once"
  BEGIN_SENSOR_TEST = "begin_sensor_test"
  STOP_SENSOR_TEST = "stop_sensor_test"
  BEGIN_READER_TEST = "begin_reader_test"
  STOP_READER_TEST = "stop_reader_test"
  CHECK_STATUS = "check_status"
  PING = "ping"

  def __str__(self):
    return self.value

class NodeTopic(enum.Enum):
  COMMANDS = "command"
  NODE_STATUS = "status"
  NODE_RESPONSE = "response"
  TAG_READINGS = "tag"
  SENSOR_READINGS = "sensor"

  def __str__(self):
    return self.value

class ResponseCodes(enum.Enum):
  SUCCESSFUL = 0x0
  NODE_RUNNING = 0x1
  NODE_STOPPED = 0x2
  SENSORS_CONN_ERR = 0x3
  READER_CONN_ERR = 0x4
  SENSOR_RUNNING = 0x5
  SENSOR_STOPPED = 0x6
  SENSOR_PAUSED = 0x7,
  MESSAGE_SENT = 0x8,
  MESSAGE_NOT_SENT = 0x9,
  MESSAGE_RECEIVED = 0x10,
  TAG_SCANNED = 0x11,
  SENSOR_READ = 0x12

  __RESPONSE_MESSAGES = {
    0x0 : "Successful",
    0x1 : "Reading Manager is running",
    0x2 : "Reading Manager is stopped",
    0x3 : "Unable to connect to sensors. Make sure GPIO pins are connected properly.",
    0x4 : "Unable to connect to readers. Try restarting the script, disconnect and reconnect the reader, or kill any process that may be using it",
    0x5 : "Sensor is running",
    0x6 : "Sensor is stopped",
    0x7 : "Sensor is paused",
    0x8 : "Message was sent",
    0x9 : "Message was not sent",
    0x10 : "Message was received",
    0x11 : "Tag was scanned"
  }

  def __str__(self):
    return __RESPONSE_MESSAGES[self.value]

class NodeResponse(enum.Enum):
  FAILED = 0
  SUCCESSFUL = 1

  def __repr__(self):
    return self.value

  def __str__(self):
    return self.name

class NodeErrorCode(enum.Enum):
  NODE_OFFLINE = 0
  INVALID_CALLBACK = 1
  NODE_BUSY_LOGGING = 2

  __ERR_MESSAGES = {
    NODE_OFFLINE : "Node is unreachable",
    INVALID_CALLBACK : "Callback function was invalid",
    NODE_BUSY_LOGGING : "Node is currently logging and cannot execute other commands until it has stopped"
  }

  def __str__(self):
    return __ERR_MESSAGES(self.name)

class Node:
  def __init__(self, id, location):
    self.__CONNECTIVITY_TIMEOUT = 2
    self.__MAX_CONNECTION_ATTEMPTS = 5

    self.__id = id
    self.__location = location
    self.__status = NodeStatus.OFFLINE
    self.__logging = NodeStatus.STOPPED
    self.__closing = False
    
    self.__node_replies = []
    self.__node_replies_lock = threading.Lock()

    self.__logging_callback = None
    self.__read_once_callback = None
    self.__sensor_callback = None
    self.__reader_callback = None

    self.__client = client.Client(transport='websockets') # Connect with websockets
    self.__client.on_connect = self.__on_connect
    self.__client.on_message = self.__on_message
    self.__client.connect('broker.hivemq.com', port=8000)

  def __str__(self):
    return f"{self.__id},{self.__location},{self.__connected},{self.__logging}"

  def BeginLogging(self, callback):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE

    if self.__logging == NodeStatus.LOGGING:
      return NodeErrorCode.NODE_BUSY_LOGGING

    if not hasattr(callback, '__call__'):
      return NodeErrorCode.INVALID_CALLBACK

    self.__logging_callback = callback
    self.__send_message(NodeCommand.START_LOGGING)

  def StopLogging(self):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE
    
    self.__logging_callback = None
    self.__send_message(NodeCommand.STOP_LOGGING)

  def ReadOnce(self, callback):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE
    
    if self.__logging == NodeStatus.LOGGING:
      return NodeErrorCode.NODE_BUSY_LOGGING

    if not hasattr(callback, '__call__'):
      return NodeErrorCode.INVALID_CALLBACK

    self.__read_once_callback = callback
    self.__send_message(NodeCommand.READ_ONCE)

  def StartSensorTest(self, callback):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE
    
    if self.__logging == NodeStatus.LOGGING:
      return NodeErrorCode.NODE_BUSY_LOGGING

    if not hasattr(callback, '__call__'):
      return NodeErrorCode.INVALID_CALLBACK
    
    self.__sensor_callback = callback
    self.__send_message(NodeCommand.BEGIN_SENSOR_TEST)

  def StopSensorTest(self):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE
    
    self.__sensor_callback == None
    self.__send_message(NodeCommand.STOP_SENSOR_TEST)

  def BeginReaderTest(self, callback):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE
    
    if self.__logging == NodeStatus.LOGGING:
      return NodeErrorCode.NODE_BUSY_LOGGING

    if not hasattr(callback, '__call__'):
      return NodeErrorCode.INVALID_CALLBACK

    self.__reader_callback = callback
    self.__send_message(NodeCommand.BEGIN_READER_TEST)

  def StopReaderTest(self):
    if self.__status == NodeStatus.OFFLINE:
      return NodeErrorCode.NODE_OFFLINE
      
    self.__reader_callback == None
    self.__send_message(NodeCommand.STOP_READER_TEST)

  def ConnectionStatus(self):
    return self.__status

  def LoggingStatus(self):
    return self.__logging    

  def GetID(self):
    return self.__id  
  
  def GetLocation(self):
    return self.__location    

  def GetNodeStatus(self):
    return self.__status

  def GetLoggingStatus(self):
    return self.__logging

  def Shutdown(self):
    self.StopLogging()
    self.StopSensorTest()
    self.StopSensorTest()

    self.__closing = True
    self.__client.disconnect()

  def __send_message(self, message, callback, timeout = 30):
    if not isinstance(timeout, int) or timeout < 0:
      print("Invalid timeout argument. Timeout must be an integer greater than 0.")
      raise ValueError

    message_send_time = datetime.datetime.now()

    def wait_for_response():
      expected_response = {'BODY' : message, 'RESPONSE_CODE' : ResponseCodes.MESSAGE_RECEIVED }
      node_response = NodeResponse.FAILED

      while node_response == NodeResponse.FAILED and (datetime.datetime.now() - message_send_time).total_seconds() <= timeout and not self.__closing:
          self.__node_replies_lock.acquire()
          
          if expected_response in self.__node_replies:
            node_response = NodeResponse.SUCCESSFUL
            self.__node_replies.remove(node_response)

          self.__node_replies_lock.release()

      if not self.__closing:
        callback(node_response)

    client.publish(f'reader/{self.ID}/{NodeTopic.COMMANDS}', str(message), qos=1)

    wait_thread = threading.Thread(target=wait_for_response)
    wait_thread.start()

  def __on_connect(self, client, data, flags, rc):
    client.subscribe(f'reader/{self.__id}/{NodeTopic.NODE_STATUS}', 1) 
    client.subscribe(f'reader/{self.__id}/{NodeTopic.NODE_RESPONSE}', 1) 
    client.subscribe(f'reader/{self.__id}/{NodeTopic.TAG_READINGS}', 1) 
    client.subscribe(f'reader/{self.__id}/{NodeTopic.SENSOR_READINGS}', 1)

    self.__check_for_connectivity()

  def __on_message(self, client, data, msg):
    message_obj = json.loads(str(msg.payload, 'utf-8'))
    topic = msg.topic.split(sep='/')[2]

    if topic == NodeTopic.NODE_STATUS:
      self.__logging = ResponseCodes[message_obj['RESPONSE_CODE']]
    elif topic == NodeTopic.NODE_RESPONSE:
      self.__node_replies_lock.acquire()
      self.__node_replies.append(message_obj)
      self.__node_replies_lock.release()
    elif topic == NodeTopic.TAG_READINGS:
      if self.__logging == NodeStatus.LOGGING and hasattr(self.__logging_callback, '__call__'):
        self.__logging_callback(message_obj['BODY'])
      elif hasattr(self.__read_once_callback, '__call__'):
        self.__read_once_callback(message_obj['BODY'])
        self.__read_once_callback = None
    elif topic == NodeTopic.SENSOR_READINGS:
      if hasattr(self.__sensor_callback, '__call__'):
        self.__sensor_callback(message_obj['BODY'])
    elif topic == NodeTopic.TAG_READINGS:
      if hasattr(self.__reader_callback, '__call__'):
        self.__reader_callback(message_obj['BODY'])

  def __check_for_connectivity(self, attempt = 0):
    def update_connectivity(node_response):
      self.__status = NodeStatus.ONLINE if NodeResponse.SUCCESSFUL else NodeStatus.OFFLINE

      if self.__status == NodeStatus.OFFLINE:
        self.__check_for_connectivity(attempt + 1)

    if not isinstance(attempt, int) or attempt < 0 or attempt > self.__MAX_CONNECTION_ATTEMPTS:
      print(f"Argument error: {attempt}. 'attempt' must be an integer > 0 and < self.__MAX_CONNECTION_ATTEMPTS")
      raise ValueError

    if attempt == self.__MAX_CONNECTION_ATTEMPTS:
      return NodeErrorCode.NODE_OFFLINE

    if self.__status == NodeStatus.OFFLINE:
      self.__send_message(NodeCommand.PING, update_connectivity, timeout=self.__CONNECTIVITY_TIMEOUT)

