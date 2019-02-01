'''
Written by Dominique Stepek
RFID Logging Software

Description:
Receives tags from scanning manager and reports the tags to the UI client through MQTT broker.

Edited on: January 31, 2019
'''

import paho.mqtt.client as mqtt

RASPI_ID = None # Unique ID to differentiate between different systems that are connected to the UI Client
conn = None # Piped connection to scanning manager

def client_connected(client, data, flags, rc):
    print('connected on ' + str(rc))

    while True:
        json = conn.recv() # Lock thread until something has been sent over pipe
        client.publish("reader/{}/active_tag".format(RASPI_ID), payload=json, qos=1) # Send tags to topic 'reader/{RASPI_ID}/active_tag'

def reporting_manager(pipe, raspi_id):
    RASPI_ID = raspi_id
    conn = pipe

    client = mqtt.Client(transport='websockets')
    client.on_connect = client_connected
    client.connect('broker.hivemq.com', port=8000)

    client.loop_forever()