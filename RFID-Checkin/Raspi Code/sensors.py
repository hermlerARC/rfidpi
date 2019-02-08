import RPi.GPIO as GPIO
import time
 
GPIO.setmode(GPIO.BCM)

SENSOR1_PINS = [18,24]
SENSOR2_PINS = []

TRIG1 = 18
ECHO1 = 24


def get_sensor1_value():

    GPIO.output(TRIG1, True)
    time.sleep(0.00001)
    GPIO.output(TRIG1, False)

    while GPIO.input(ECHO1) == 0:
        pass
        pulse_start1 = time.time()
        
     
    while GPIO.input(ECHO1) == 1:
        pass
        pulse_end1 = time.time()

    pulse_duration1 = pulse_end1 - pulse_start1

    distance1 = pulse_duration1 * 17150
    distance1= round(distance1, 2)
    
    return distance1
    
def get_sensor2_value():
    GPIO.output(TRIG1, True)
    time.sleep(0.00001)
    GPIO.output(TRIG1, False)

    while GPIO.input(ECHO1) == 0:
        pass
        pulse_start = time.time()
        
     
    while GPIO.input(ECHO1) == 1:
        pass
        pulse_end = time.time()

    pulse_duration = pulse_end1 - pulse_start

    distance = pulse_duration * 17150
    distance = round(distance, 2)
    
    return distance

def setup():
    
    GPIO.setup(SENSOR1_PINS[0], GPIO.OUT)
    GPIO.output(SENSOR1_PINS[0], False)

    GPIO.setup(SENSOR1_PINS[1], GPIO.IN)

GPIO.cleanup()