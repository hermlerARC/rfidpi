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
reporting_process = None # Process that handles RFID tag read reporting to the MQTT Broker
scanning_process = None # Process that handles continuous checking off sensors and RFID reader
reporting_conn, scanner_conn = Pipe() # Connect two processes by pipe

def client_messaged(client, data, msg):
    # When 'read' is posted on the topic 'reader/{RASPI_ID}/status'
    # Initialize and start reporting_process and scanning_process
    if (msg.payload == b'read'): 
        reporting_process = Process(target=reporting_manager.reporting_manager, args=(reporting_process, RASPI_ID))
        scanning_process = Process(target=scanning_manager.scanning_manager, args=(scanner_conn))
        reporting_process.start() 
        scanning_process.start()
    # Read for RFID tags and mark as heading 'in'. Publish to MQTT topic 'reader/{RASPI_ID}/active_tag'
    elif (msg.payload == b'read_once'):
        reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
        reader.set_region('NA')
        
        active_tags = scanning_manager.get_tags('in', reader)
        client.publish('reader/{}/active_tag'.format(RASPI_ID), json.dumps(active_tags), qos=1)
    # When 'stop' is posted on the topic 'reader/{RASPI_ID}/status'
    # Kill reporting_process and scanning_process
    elif (msg.payload == b'stop'):
        if reporting_process != None:
            reporting_process.terminate()
            reporting_process = None
        if scanning_process != None:
            scanning_process.terminate()
            scanning_process = None

def client_connected(client, data, flags, rc):
    print('connected on ' + str(rc))
    client.subscribe('reader/{}/status'.format(RASPI_ID)) # Setup client to receive messages posted on 'reader/{RASPI_ID}/status' topic

if __name__ == '__main__':
    client = mqtt.Client(transport='websockets')
    client.on_connect = client_connected
    client.on_message = client_messaged
    client.connect('broker.hivemq.com', port=8000)

    client.loop_forever()