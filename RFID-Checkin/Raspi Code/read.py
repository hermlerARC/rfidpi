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


#TODO: Rework handler.py to support new node topics and commands

from paho.mqtt import client as mqtt, publish
from response_codes import ResponseCodes
from reading_manager import ReadingManager
from sensors import SensorManager
import json, mercury, datetime, enum

# Unique ID to differentiate between different systems that are connected to the UI Client
RASPI_ID = 'UPOGDU'
LOG_FILE = "System Logs/{}.txt" # {} Are replaced by a datetime value in print_out()
DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'

READER_PATH = "tmr:///dev/ttyUSB"

class NodeTopic(enum.Enum):
  COMMANDS = "command"
  NODE_STATUS = "status"
  NODE_RESPONSE = "response"
  TAG_READINGS = "tag"
  SENSOR_READINGS = "sensor"

  def __str__(self):
    return self.value

def print_out(msg):
  """
  Prints data to the LOG_FILE and out to the screen.
  """
  curr_time = datetime.datetime.now()
  ft_msg = "{}\t{}".format(curr_time.strftime(DATETIME_FORMAT), msg)

  print(ft_msg)
  with open(LOG_FILE.format(curr_time.strftime('%m-%d-%Y')), 'a') as LF:
    LF.write(ft_msg)

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

      return [ResponseCodes.SUCCESSFUL, reader, "{}{}".format(path, conn_port)]
    except:
      pass

  return [ResponseCodes.READER_CONN_ERR, reader, ""]

def send_message(client, topic, msg, code):
  if isinstance(client, mqtt.Client) and isinstance(topic, NodeTopic):
    message_object = {
      'BODY' : msg,
      'RESPONSE_CODE' : ""
    }

    if isinstance(code, ResponseCodes):
      message_object['RESPONSE_CODE'] = code.value
    elif isinstance(code, int):
      message_object['RESPONSE_CODE'] = code
  
    client.publish('reader/{}/{}'.format(RASPI_ID, topic), json.dumps(message_object), qos=1)
    return ResponseCodes.MESSAGE_SENT
  else:
    print('topic argument must be an instance of a NodeTopic')
    raise ValueError
    return ResponseCodes.MESSAGE_NOT_SENT

def client_messaged(client, data, msg):
  print_out('received message {}'.format(str(msg, 'utf-8')))

  def log_tag(tag):
    send_message(client, NodeTopic.TAG_READINGS, tag.to_object(), ResponseCodes.TAG_SCANNED)

  def log_sensor_reading(sensor_reading):
    send_message(client, NodeTopic.SENSOR_READINGS, sensor_reading.to_object(), ResponseCodes.SENSOR_READ)

  if (msg.payload == b'start_logging'):
    send_message(client, NodeTopic.NODE_STATUS, '', reading_man.BeginReading(callback=log_tag))
    print_out('starting reading manager...')

  elif (msg.payload == b'stop_logging'):
    send_message(client, NodeTopic.NODE_STATUS, '', reading_man.StopReading())
    print_out('stopping reading manager')

  elif (msg.payload == b'read_once'):
    tag = reading_man.ReadOnce()
    print_out("read tag with EPC: {}".format(tag.epc))
    log_tag(tag)

  elif (msg.payload == b'begin_sensor_test'):
    print_out('beginning sensor test...')
    sensor_man.RunSensors(callback=log_sensor_reading)

  elif (msg.payload == b'stop_sensor_test'):
    sensor_man.StopSensors()
    print_out('stopping sensor test...')

  elif (msg.payload == b'begin_reader_test'):
    print_out('beginning reader test...')
    reading_man.BeginReading(callback=log_tag, testing=True)

  elif (msg.payload == b'stop_reader_test'):
    reading_man.StopReading()
    print_out('stopping reader test...')

  elif (msg.payload == b'check_status'):
    send_message(client, NodeTopic.NODE_STATUS, "", reading_man.IsRunning())

  send_message(client, NodeTopic.NODE_RESPONSE, str(msg.payload, 'utf-8'), ResponseCodes.MESSAGE_RECEIVED)

def client_connected(client, data, flags, rc):
  client.subscribe('reader/{}/{}'.format(RASPI_ID, NodeTopic.COMMANDS), 1)
  print_out("listening for commands on 'reader/{}/{}'".format(RASPI_ID, NodeTopic.COMMANDS))

if __name__ == '__main__':
  # Attempt to connect to reader
  reader_response, reader, conn_path = connect_to_reader()
  if reader_response == ResponseCodes.SUCCESSFUL:
    print_out("connected to reader on '{}'".format(conn_path))
  else:
    print_out(str(reader_response))
    exit(1)

  sensor_man = SensorManager()
  reading_man = ReadingManager(reader, sensor_man)

  # Attempt to connect to MQTT
  client = mqtt.Client(transport='websockets')  # Connect with websockets
  client.on_connect = client_connected
  client.on_message = client_messaged
  client.connect('broker.hivemq.com', port=8000)

  try:
    client.loop_forever() # Handles reconnecting to MQTT server upon timeout automatically
  except:
    reading_man.StopReading()
    sensor_man.StopSensors()

    print_out("closing read.py")