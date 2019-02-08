'''
Written by Dominique Stepek
RFID Logging Software

Description:
Receives tags from scanning manager and reports the tags to the UI client through MQTT broker.

Edited on: January 31, 2019
'''

import paho.mqtt.publish as publish

RASPI_ID = None # Unique ID to differentiate between different systems that are connected to the UI Client
conn = None # Piped connection to scanning manager

def reporting_manager(pipe, raspi_id):
    RASPI_ID = raspi_id
    conn = pipe
    
    while True:
        json = conn.recv()
        print(json)
        publish.single("reader/{}/active_tag".format(raspi_id), json, hostname="broker.hivemq.com", qos=1)
    
