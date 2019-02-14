import RPi.GPIO as GPIO
import time, datetime
 
SENSOR1_PINS = [18,24]
SENSOR2_PINS = [17,23]

def get_sensor1_value():

    GPIO.output(SENSOR1_PINS[0], True)
    time.sleep(0.00001)
    GPIO.output(SENSOR1_PINS[0], False)

    while GPIO.input(SENSOR1_PINS[1]) == 0:
        pulse_start = time.time()
        
     
    while GPIO.input(SENSOR1_PINS[1]) == 1:
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
        pulse_start = time.time()
        
     
    while GPIO.input(SENSOR2_PINS[1]) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150
    distance = round(distance, 2)
    
    return distance

def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(SENSOR1_PINS[0], GPIO.OUT)
    GPIO.setup(SENSOR2_PINS[0], GPIO.OUT)
    
    GPIO.setup(SENSOR1_PINS[1], GPIO.IN)
    GPIO.setup(SENSOR2_PINS[1], GPIO.IN)
    
    GPIO.output(SENSOR1_PINS[0], False)
    GPIO.output(SENSOR2_PINS[0], False)
    
    time.sleep(2)



def test_sensors(threshold = 100):
	setup()
	try:
		print('Time\tSensor\tValue')
		while True:
			v1 = get_sensor1_value()
			v2 = get_sensor2_value()
			t = str(datetime.datetime.now().isoformat())
			
			if (v1 < threshold):
				print(t + '\t1\t' + str(v1) + " cm")
			if (v2 < threshold):
				print(t + '\t2\t' + str(v2) + " cm")
			
			time.sleep(.25)
	except KeyboardInterrupt:
		print('Stopped tests.')
		pass

