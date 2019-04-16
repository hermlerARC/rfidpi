'''
RFID Logging Software

Description (response_codes.py):
Codes that describe status of the current state of the node, RFID reader, sensors, and MQTT client.

Contributors:
Dom Stepek

Source code: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/

Edited on: March 21, 2019
'''

import enum

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
    0x11 : "Tag was scanned",
    0x12 : "Sensor reported data"
  }

  def __str__(self):
    return __RESPONSE_MESSAGES(self.name)