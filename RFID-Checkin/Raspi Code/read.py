'''
RFID Logging Software

Description (read.py): 
Main script to run the Raspberry PI that handles creating and terminating the 
reporting and scanning processes. Receives calls from UI Client to read, read once, and stop reading.

Contributors:
Dom Stepek, Gavin Furlong

To read more about Mercury API for Python go to: https://github.com/gotthardp/python-mercuryapi

Edited on: February 19, 2019
'''

from multiprocessing import Process, Pipe
import paho.mqtt.client as mqtt
import reporting_manager, scanning_manager, reading_manager, json, mercury, sensors, sys

RASPI_ID = 'UPOGDU' # Unique ID to differentiate between different systems that are connected to the UI Client
processes = [] # Handles processes that manage RFID tag reading and reporting to MQTT
reader_connected = False
reader_port = 0

# Configure ThingMagic RFID Reader on USB port
while not reader_connected:
    try:
        reader = mercury.Reader("tmr:///dev/ttyUSB{}".format(reader_port), baudrate=9600)
        reader.set_region('NA')
        reader_connected = True
        print('connected to reader on port {}'.format(reader_port))
    except:
        reader_port = reader_port + 1

def client_messaged(client, data, msg):
    # When 'read' is posted on the topic 'reader/{RASPI_ID}/status'
    # Initialize and start reporting_process and scanning_process
    if (msg.payload == b'read'):
            
        reporting_conn, scanner_conn1 = Pipe() # Connect two processes by pipe
        reading_conn, scanner_conn2 = Pipe()
        
        reporting_process = Process(target=reporting_manager.reporting_manager, args=(reporting_conn, RASPI_ID))
        reading_process = Process(target=reading_manager.reading_manager, args=(reading_conn, reader))
        scanning_process = Process(target=scanning_manager.scanning_manager, args=(scanner_conn1, scanner_conn2))
        
        # Daemon exits each process if the main process is killed
        reporting_process.daemon = True
        reading_process.daemon = True
        scanning_process.daemon = True
        
        reporting_process.start() 
        reading_process.start()
        scanning_process.start()
        
        processes.extend((reporting_process, reading_process, scanning_process))
            
    # Read for RFID tags and mark as heading 'in'. Publish to MQTT topic 'reader/{RASPI_ID}/active_tag'
    
    elif (msg.payload == b'read_once'):
        tag_data = reading_manager.read_once(reader)
        active_tags = scanning_manager.create_tags(tag_data, 0)
        client.publish('reader/{}/active_tag'.format(RASPI_ID), json.dumps(active_tags), qos=1)
            
    # When 'stop' is posted on the topic 'reader/{RASPI_ID}/status'
    # Kill reporting_process and scanning_process
    
    elif (msg.payload == b'stop'):
        processes[0].terminate()
        processes[1].terminate()
        processes[2].terminate()
            
    # When 'test_sensors' is posted on the topic 'reader/{RASPI_ID}/status'
    # Test sonar sensors
    elif (msg.payload == b'test_sensors'):
        print('Beginning test... press control+c to stop')
        sensors.test_sensors(100)
            
    # When 'test_reader' is posted on the topic 'reader/{RASPI_ID}/status'
    # Test RFID reader
    elif (msg.payload == b'test_reader'):
        print('Beginning test... press control+c to stop')
        reading_manager.test_reader(reader)

def client_connected(client, data, flags, rc):
    print('connected to client on \'reader/{}/status\''.format(RASPI_ID))
    client.subscribe('reader/{}/status'.format(RASPI_ID)) # Setup client to receive messages posted on 'reader/{RASPI_ID}/status' topic

if __name__ == '__main__':
    client = mqtt.Client(transport='websockets') # Connect with websockets
    client.on_connect = client_connected
    client.on_message = client_messaged
    client.connect('broker.hivemq.com', port=8000)

    client.loop_forever() # Prevents MQTT client from prematurely closing
