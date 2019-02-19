'''
RFID Logging Software

Description (reporting_manager.py):
Receives tags from scanning manager and reports the tags to the UI client through MQTT broker.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: February 19, 2019
'''

import paho.mqtt.publish as publish


def reporting_manager(pipe, raspi_id):
    RASPI_ID = raspi_id
    conn = pipe
    
    while True:
        json = conn.recv() # Block thread until tag is scanned
        publish.single("reader/{}/active_tag".format(raspi_id), json, hostname="broker.hivemq.com", qos=1) # Send tag(s) to topic
    
