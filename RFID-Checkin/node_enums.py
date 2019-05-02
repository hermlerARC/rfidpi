import enum, hashlib

class Status(enum.Enum):
  ONLINE = "online"
  OFFLINE = "offline"

  LOGGING = "logging"
  REQUESTING_TAG = "requesting single tag" 
  RUNNING_SENSOR_TEST = "running sensor test"
  RUNNING_READER_TEST = "running reader test"

class Command(enum.Enum):
  START_LOGGING = "start_logging"
  STOP_LOGGING = "stop_logging"
  READ_ONCE = "read_once"
  BEGIN_SENSOR_TEST = "begin_sensor_test"
  STOP_SENSOR_TEST = "stop_sensor_test"
  BEGIN_READER_TEST = "begin_reader_test"
  STOP_READER_TEST = "stop_reader_test"
  CHECK_STATUS = "check_status"
  GET_LOGS = "get_logs"
  PING = "ping"

  def __str__(self):
    return self.value

  def __repr__(self):
    return hashlib.sha1(bytes(self.value, 'utf-8')).hexdigest()

class Topic(enum.Enum):
  COMMANDS = "command"
  NODE_STATUS = "status"
  NODE_RESPONSE = "response"
  TAG_READINGS = "tag"
  SENSOR_READINGS = "sensor"
  ERROR_CODES = 'errors'
  NODE_LOG = 'logs'

  def __str__(self):
    return self.value

class NodeBusy(Exception):
  def __init__(self, error):
    if isinstance(error, NodeError):
      self.Error = error
      self.Message = str(error)
    elif isinstance(error, int):
      self.Error = NodeError(error)
      self.Message = str(NodeError(error))

def ReaderUnreachable(Exception):
  pass

class NodeError(enum.Enum):
  NODE_OFFLINE = 1
  INVALID_CALLBACK = 2
  NODE_BUSY_LOGGING = 3
  NODE_BUSY_TESTING_SENSORS = 4
  NODE_BUSY_TESTING_READER = 5
  NODE_BUSY_REQUESTING_TAG = 6

  __ERR_MESSAGES = {
    NODE_OFFLINE : "Node is unreachable",
    INVALID_CALLBACK : "Callback function was invalid",
    NODE_BUSY_LOGGING : "Node is currently logging and cannot perform another action until it has stopped",
    NODE_BUSY_TESTING_SENSORS : "Node is currently running a sensor test and cannot perform another action until it has stopped",
    NODE_BUSY_TESTING_READER : "Node is currently running a reader test and cannot perform another action until it has stopped",
    NODE_BUSY_REQUESTING_TAG : "Node is currently requesting a tag from the reading manager and cannot perform another action until it has finished"
  }

  def __str__(self):
    return __ERR_MESSAGES(self.name)