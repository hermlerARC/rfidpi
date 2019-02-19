'''
RFID Logging Software

Description (sensors.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Source code: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/

Edited on: February 19, 2019
'''

import RPi.GPIO as GPIO
import time, datetime

IN_PINS = [18,24]
OUT_PINS = [17,23]

def get_sensor_value(sensor):
	# Read from either IN_PINS or OUT_PINS
	pins = IN_PINS if sensor == 'in' else OUT_PINS
	
	# Set 'Trigger' pin to HIGH
	GPIO.output(pins[0], True)
	
	# Set 'Trigger' pin after 0.01ms to LOW
	time.sleep(0.00001)
	GPIO.output(pins[0], False)

	start_time = time.time()
	stop_time = time.time()

	# Save start_time
	while GPIO.input(pins[1]) == 0:
		start_time = time.time()
		
	# Save time of arrival
	while GPIO.input(pins[1]) == 1:
		stop_time = time.time()

	# Time between start_time and time of arrival
	time_elapsed = stop_time - start_time

	# Multiply time_elapsed by speed of sound divided by two because sound traveled the distance to object and back.
	distance = time_elapsed * 17150
	
	return distance


def setup():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)

	# Set GPIO directions (IN / OUT)
	GPIO.setup(IN_PINS[0], GPIO.OUT)
	GPIO.setup(OUT_PINS[0], GPIO.OUT)
	
	GPIO.setup(IN_PINS[1], GPIO.IN)
	GPIO.setup(OUT_PINS[1], GPIO.IN)
	
	time.sleep(2)

def test_sensors(threshold = 100):
	setup()
	try:
		print('Time\tSensor\tValue')
		while True:
			v1 = get_sensor_value('in')
			v2 = get_sensor_value('out')
			t = str(datetime.datetime.now().isoformat())
			
			if (v1 < threshold):
				print(t + '\t1\t' + str(v1) + " cm")
			if (v2 < threshold):
				print(t + '\t2\t' + str(v2) + " cm")
			
			time.sleep(.25)
	except KeyboardInterrupt:
		print('Stopped tests.')
		pass

