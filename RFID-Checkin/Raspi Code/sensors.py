import RPi.GPIO as GPIO
import time
 
SENSOR1_PINS = [18,24]
SENSOR2_PINS = [17,23]

def get_sensor1_value():

    GPIO.output(SENSOR1_PINS[0], True)
    time.sleep(0.00001)
    GPIO.output(SENSOR1_PINS[0], False)

    while GPIO.input(SENSOR1_PINS[1]) == 0:
        pass
        pulse_start = time.time()
        
     
    while GPIO.input(SENSOR1_PINS[1]) == 1:
        pass
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150
    distance = round(distance, 2)
    
    return distance
    
def get_sensor2_value():
    GPIO.output(SENSOR2_PINS[0], True)
    time.sleep(0.00001)
    GPIO.output(SENSOR2_PINS[0], False)

    while GPIO.input(SENSOR2_PINS[1]) == 0:
        pass
        pulse_start = time.time()
        
     
    while GPIO.input(SENSOR2_PINS[1]) == 1:
        pass
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150
    distance = round(distance, 2)
    
    return distance

def setup():
    GPIO.cleanup()
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(SENSOR1_PINS[0], GPIO.OUT)
    GPIO.setup(SENSOR2_PINS[0], GPIO.OUT)
    
    GPIO.output(SENSOR1_PINS[0], False)
    GPIO.output(SENSOR2_PINS[0], False)

    GPIO.setup(SENSOR1_PINS[1], GPIO.IN)
    GPIO.setup(SENSOR2_PINS[1], GPIO.IN)

'''
setup()
while True:
    print("sensor 1: " + str(get_sensor1_value()) + " cm")
    print("sensor 2: " + str(get_sensor2_value()) + " cm")
    
    time.sleep(1)
'''