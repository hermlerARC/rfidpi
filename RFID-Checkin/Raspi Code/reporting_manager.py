'''
RFID Logging Software

Description (reporting_manager.py):
Receives tags from scanning manager and reports the tags to the UI client through MQTT broker.

Contributors:
Dom Stepek, Gavin Furlong

Edited on: March 21, 2019
'''

import paho.mqtt.publish as publish

process_running = True

def set_process(val):
    global process_running
    process_running = val

def reporting_manager(pipe, raspi_id):
    conn = pipe
    
    while process_running:
        json = conn.recv() # Block thread until tag is scanned
        print(json)
        publish.single("reader/{}/active_tag".format(raspi_id), json, hostname="broker.hivemq.com", qos=1) # Send tag(s) to topic
