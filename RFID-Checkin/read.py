import datetime, uuid, json, time, mercury, threading, queue
import paho.mqtt.client as mqtt
from gpiozero import LightSensor

RASPI_ID = 'UPOGDU'

laser_queue = queue.Queue()
status = [False]

laser_in = laser("north main door")
laser_out = laser("north main door")

loop_thread = threading.Thread(target=laser.check_lasers)

class tag:
    def __init__(self, epc, status, location):
        self.epc = epc
        self.datetime = datetime.datetime.now()
        self.status = status
        self.location = location
    def toJSON(self):
        return 
        {
            "EPC" : self.epc,
            "Timestamp" : self.datetime.isoformat(),
            "Status" : 0 if self.status == 'in' else 1,
            "Location" : self.location
        }
    @staticmethod
    def get_tags(status):
        all_tags = []
        all_tag_data = reader.read()

        for tag_data in all_tag_data:
            epc = str(tag_data.epc, 'utf-8')
            all_tags.append(tag(epc, status).toJSON())

        return all_tags

class laser:
    def __init__(self, location):
        self.location = location
    @staticmethod
    def check_lasers(stat):
        ldr_in = LightSensor(4) 
        ldr_out = LightSensor(17)
        tripped_laser = None
        trip_time = None
        active_tags = []
        client = laser_queue.get() 

        while stat[0]:
            if tripped_laser == None:
                if ldr_in.value < 1000: 
                    trip_time = datetime.datetime.now()
                    tripped_laser = 0 
                    active_tags = tag.get_tags('out') 
                elif ldr_out.value < 1000: 
                    trip_time = datetime.datetime.now()
                    tripped_laser = 1
                    active_tags = tag.get_tags('in') 
            if (datetime.datetime.now() - trip_time).total_seconds() < 3: 
                if (ldr_in.value < 1000 and tripped_laser == 1) or (ldr_out.value < 1000 and tripped_laser == 0): 

                    client.publish('reader/{}/active_tag'.format(RASPI_ID), json.dumps(active_tags), qos=1)
            else:
                trip_time = None

def on_message(client, data, msg): 
    if (msg.payload == b'read_once'):
        active_tag = tag(str(reader.read()[0].epc, 'utf-8'), "in")
        client.publish('reader/{}/active_tag'.format(RASPI_ID), json.dumps(active_tag.toJSON()), qos=1)
    if (msg.payload == b'read'):
        laser_queue.put(client)
        loop_thread.start()
    if (msg.payload == b'stop'):
        loop_thread._stop

def on_connect(client, data, flags, rc):
    print('connected with result code ' + str(rc))
    client.subscribe('reader/status')

reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
reader.set_region('NA')

client = mqtt.Client(transport='websockets')
client.on_message=on_message
client.on_connect=on_connect
client.connect('broker.hivemq.com', port=8000)

client.loop_forever()