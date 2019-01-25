import datetime, uuid, json, time, mercury
import paho.mqtt.client as mqtt

active_tags = []
class tag:
    def __init__(self, epc, status):
        self.epc = epc
        self.datetime = datetime.datetime.now()
        self.status = status
    def toJSON(self):
        return {"EPC" : self.epc, "Timestamp" : self.datetime.isoformat(), "Status" : 0 if self.status == 'in' else 1}

def addTags(tags, reader):
    log_tags = []
    for tag_data in tags:
        epc = str(tag_data.epc, 'utf-8')
        old_tag = next((x for x in active_tags if x.epc == epc), None)
        new_tag = tag(epc, reader)

        if old_tag != None:
            if (new_tag.datetime - old_tag.datetime).total_seconds() < 61:
                log_tags.append(tag(epc, new_tag.status))
            else:
                active_tags.remove(old_tag)
        else:
            active_tags.append(new_tag)
    return log_tags

def get_active_tags():
    active_tags = []

    while not active_tags:
        active_tags.extend(addTags(in_reader.read(timeout=10), "in"))
        active_tags.extend(addTags(out_reader.read(timeout=10), "out"))

    return active_tags


def on_message(client, data, msg):  
    if (msg.payload == b'read_once'):
        active_tag = tag(str(in_reader.read()[0].epc, 'utf-8'), "in")
        client.publish('reader/active_tag', json.dumps(active_tag.toJSON()), qos=1)
        active_tags.clear()
    if (msg.payload == b'read'):
        tags = get_active_tags()
        log_tags = []
        for x in tags:
            log_tags.append(x.toJSON())
        client.publish('reader/active_tag', json.dumps(log_tags), qos=1)
        active_tags.clear()

def on_connect(client, data, flags, rc):
    print('connected with result code ' + str(rc))
    client.subscribe('reader/status')

in_reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
out_reader = mercury.Reader("tmr:///dev/ttyUSB1", baudrate=9600)
in_reader.set_region('NA')
out_reader.set_region('NA')

client = mqtt.Client(transport='websockets')
client.on_message=on_message
client.on_connect=on_connect
client.connect('broker.hivemq.com', port=8000)

client.loop_forever()