'''
RFID Logging Software

Description (sensors.py):
Handles sensors that detect whether RFID tag is leaving or entering structure and reports to the
reporting manager which tags are read.

Contributors:
Dom Stepek, Gavin Furlong

Source code: https://tutorials-raspberrypi.com/raspberry-pi-ultrasonic-sensor-hc-sr04/

Edited on: March 21, 2019
'''

import RPi.GPIO as GPIO
import time, datetime, threading

thread_counter = 0
active_threads = []
IN_PINS = [18,23]
OUT_PINS = [25,24]
READ_SPEED = 10 # 10 reads per second

def get_sensor_value(sensor):
    # Read from either IN_PINS or OUT_PINS
    pins = IN_PINS if sensor == 0 else OUT_PINS
    
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
    GPIO.setmode(GPIO.BCM)

    # Set GPIO directions (IN / OUT)
    GPIO.setup(IN_PINS[0], GPIO.OUT)
    GPIO.setup(OUT_PINS[0], GPIO.OUT)
    
    GPIO.setup(IN_PINS[1], GPIO.IN)
    GPIO.setup(OUT_PINS[1], GPIO.IN)
    
def begin_reading(sensor, callback):
    """
    Creates a new thread to run a reader and calls the callback function everytime it gets a read
    
    Keyword arguments:
        sensor -- Either '0' or '1' for in or out reader, respectively
        callback -- Function that should have 2 parameters. Calls the function with the id and reading of the sensor.
    """
    global READ_SPEED
    global active_threads
    global thread_counter
    
    def read_sensors(sensor, callback, thread_count):
        while True:
            if active_threads[thread_count] == 0: # Pause
                pass
            elif active_threads[thread_count] == 1: # Run
                callback(sensor, get_sensor_value(sensor))
                time.sleep(1/READ_SPEED)
            elif active_threads[thread_count] == 2: # Exit
                break
    
    
    active_threads.append(1) # Add the 'run' status to the active_threads list
    threading.Thread(target=read_sensors, args=(sensor, callback, thread_counter)).start()
    thread_counter += 1
    return thread_counter - 1


def set_read_status(thread_count, status):
    """
    Tell a sensor to pause, resume, or stop.
    
    Keyword arguments:
        thread_count -- the ID associated with the thread the sensor reads on
        status -- 0 for pause, 1 for resume, 2 for stop
    """
    
    global active_threads
    active_threads[thread_count] = status


def test_sensors(threshold = 100):
    """
    Prints out sensor reading every 1/READ_SPEED seconds. Stops reading with input from keyboard.
    
    Keyword arguments:
        threshold -- Max distance in cm that the sonic readers reports. Default is 100 cm.
    """
    
    # Function that prints out to the standard output a line formatted as "{Time}  {Sensor}  {Read value}"
    def print_reading(sensor, reading):
        if reading < threshold:
            t = str(datetime.datetime.now().isoformat())
            print ("{}\t{}\t{}".format(t, 'in' if sensor == 1 else 'out', reading))
    
    in_thread  = begin_reading(0, print_reading)
    out_thread = begin_reading(1, print_reading)       

    input()

    set_read_status(in_thread, 2)
    set_read_status(out_thread, 2)
    print('Stopped tests.')

