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

from paho.mqtt import client as mqtt, publish
from multiprocessing import Process, Pipe
from response_codes import ResponseCodes
from reading_manager import ReadingManager
import RPi.GPIO as GPIO
import repoting_manager, scanning_manager, reading_manager, json, mercury, sensors, datetime

# Unique ID to differentiate between different systems that are connected to the UI Client
RASPI_ID = 'UPOGDU'
processes = []  # Handles processes that manage RFID tag reading and reporting to MQTT
running = False

LOG_FILE = "System Logs/{}.txt" # {} Are replaced by a datetime value in print_out()
DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'

READER_PATH = "tmr:///dev/ttyUSB"

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

def client_messaged(client, data, msg):
  # Response Message
  js = json.dumps({
    'NODE' : RASPI_ID,
    'MESSAGE' : str(msg.payload, 'utf-8'),
    'CODE' : '0x0'
  })

  if (msg.payload == b'read'):
    reading_man.BeginReading()
  # Read for RFID tags and mark as heading 'in'. Publish to MQTT topic 'reader/{RASPI_ID}/active_tag'

  elif (msg.payload == b'read_once'):
    js = json.dumps(reading_man.ReadOnce())
    client.publish('reader/{}/scanned'.format(RASPI_ID), json.dumps(tag_data), qos=1)

  # When 'stop' is posted on the topic 'reader/{RASPI_ID}/status'
  # Kill reporting_process and scanning_process

  elif (msg.payload == b'stop'):
    reading_man.StopReading()

  # When 'test_sensors' is posted on the topic 'reader/{RASPI_ID}/status'
  # Test sonar sensors
  elif (msg.payload == b'test_sensors'):
    print('Beginning test... press control+c to stop')
    sensors.test_sensors(300)

  # When 'test_reader' is posted on the topic 'reader/{RASPI_ID}/status'
  # Test RFID reader
  elif (msg.payload == b'test_reader'):
    print('Beginning test... press control+c to stop')
    reading_manager.test_reader(reader)

  elif (msg.payload == b'get_data'):
    pass

  js = json.dumps({'MESSAGE': str(msg.payload, 'utf-8')})
  client.publish('reader/{}/response'.format(RASPI_ID), js, qos=1)

def client_connected(client, data, flags, rc):
  # Setup client to receive messages posted on 'reader/{RASPI_ID}/status' topic
  client.subscribe('reader/{}/status'.format(RASPI_ID), 1)
  print_out("listening for commands on 'reader/{}/status'".format(RASPI_ID))

if __name__ == '__main__':
  # Attempt to setup sensors
  sensor_response = sensors.setup()

  if sensor_response == ResponseCodes.SUCCESSFUL:
    print_out('connected to sensors')
  else:
    print_out(str(sensor_response))
    exit(1)

  # Attempt to connect to reader
  reader_response, reader, conn_path = connect_to_reader()
  if reader_response == ResponseCodes.SUCCESSFUL:
    print_out("connected to reader on '{}'".format(conn_path))
  else:
    print_out(str(reader_response))
    exit(1)

  reading_man = ReadingManager(reader)

  # Attempt to connect to MQTT
  client = mqtt.Client(transport='websockets')  # Connect with websockets
  client.on_connect = client_connected
  client.on_message = client_messaged
  client.connect('broker.hivemq.com', port=8000)

  try:
    client.loop_forever() # Handles reconnecting to MQTT server upon timeout automatically
  except:
    # Close all processes
    for process in processes:
      process.terminate()

    GPIO.cleanup() # Frees up ownership of GPIO pins
    del reader # Disconnects the reader
    print_out("closing read.py")