import enum

class ResponseCodes(enum.Enum):
  SUCCESSFUL = 0x0
  NODE_RUNNING = 0x1
  SENSORS_CONN_ERR = 0x2
  READER_CONN_ERR = 0x3
  SENSOR_RUNNING = 0x4
  SENSOR_STOPPED = 0x5
  SENSOR_PAUSED = 0x6
  READER_RUNNING = 0x7
  READER_STOPPED = 0x8

  __RESPONSE_MESSAGES = {
    0x0 : "Successful",
    0x1 : "Attempted to start a node that is already running",
    0x2 : "Unable to connect to sensors. Make sure GPIO pins are connected properly.",
    0x3 : "Unable to connect to readers. Try restarting the script, disconnect and reconnect the reader, or kill any process that may be using it",
    0x4 : "Sensor is running",
    0x5 : "Sensor is stopped",
    0x6 : "Sensor is paused",
    0x7 : "Reader is runnng",
    0x8 : "Reader is stopped"
  }

  def __str__(self):
    return __RESPONSE_MESSAGES[self.value]