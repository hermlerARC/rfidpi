'''
Written by Dominique Stepek
RFID Logging Software

Description: 
Main script to run the Raspberry PI that handles creating and terminating the 
reporting and scanning processes. Receives calls from UI Client to read, read once, and stop reading.

Edited on: January 31, 2019
'''

from multiprocessing import Process, Pipe
import paho.mqtt.client as mqtt
import reporting_manager, scanning_manager, json, mercury

RASPI_ID = 'UPOGDU' # Unique ID to differentiate between different systems that are connected to the UI Client
processes = [] # Handles processes that manage RFID tag reading and reporting to MQTT

# Configure ThingMagic RFID Reader on USB0
reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
reader.set_region('NA')

def client_messaged(client, data, msg):
    # When 'read' is posted on the topic 'reader/{RASPI_ID}/status'
    # Initialize and start reporting_process and scanning_process
    if (msg.payload == b'read'):
        reporting_conn, scanner_conn = Pipe() # Connect two processes by pipe
        reporting_process = Process(target=reporting_manager.reporting_manager, args=(reporting_conn, RASPI_ID))
        scanning_process = Process(target=scanning_manager.scanning_manager, args=(scanner_conn, reader))
        reporting_process.start() 
        scanning_process.start()
        processes.extend((reporting_process, scanning_process))
    # Read for RFID tags and mark as heading 'in'. Publish to MQTT topic 'reader/{RASPI_ID}/active_tag'
    elif (msg.payload == b'read_once'):
        active_tags = scanning_manager.get_tags('in', reader)
        client.publish('reader/{}/active_tag'.format(RASPI_ID), json.dumps(active_tags), qos=1)
    # When 'stop' is posted on the topic 'reader/{RASPI_ID}/status'
    # Kill reporting_process and scanning_process
    elif (msg.payload == b'stop'):
        processes[0].terminate()
        processes[1].terminate()

def client_connected(client, data, flags, rc):
    print('connected to client on \'reader/{}/status\''.format(RASPI_ID))
    client.subscribe('reader/{}/status'.format(RASPI_ID)) # Setup client to receive messages posted on 'reader/{RASPI_ID}/status' topic

if __name__ == '__main__':
    client = mqtt.Client(transport='websockets')
    client.on_connect = client_connected
    client.on_message = client_messaged
    client.connect('broker.hivemq.com', port=8000)

    client.loop_forever()
