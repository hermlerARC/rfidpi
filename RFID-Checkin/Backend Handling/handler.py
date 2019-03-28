from googleapiclient.discovery import build
from google.oauth2 import service_account
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import node, log, rfidtag, re, json, pickle, io, datetime

#region Variable Initialization

SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Read and write permissions for program
SPREADSHEET_IDS = '1qrFQxaisVqFPFmdBzI8MSJnH-PSuc9i2sePcdpA0_PI' # Spreadsheet ID for list of ids, names, and clubs

NODES_RANGE = 'readers!a2:b'
STATUS_RANGE = 'ids!a2:f'
LOGS_RANGE = 'log!a2:g'

HANDLER_FILE = 'handler.rsf'
SERVICE_ACCOUNT_FILE = 'service_account.json'

nodes = []
rfid_tags = []
logs = []

log_stream = None
status_stream = None

#endregion

#region Client Handling

def on_message(client, data, msg):
  js = json.load(str(msg.payload, 'utf-8'))
  curr_node = next(n for n in nodes if n.id == re.search('\/(.+)\/', msg.topic).group(1))
  
  for item in js:
    curr_tag_index = rfid_tags.index(next(t for t in rfid_tags if t.EPC == item.EPC))
    rfid_tags[curr_tag_index].Node = curr_node
    rfid_tags[curr_tag_index].Status = rfidtag.Status(item.Status)

    l = log.Log(rfid_tags[curr_tag_index], item.Timestamp, curr_node)

  with open(HANADLER_FILE, mode='a') as logf:
    pass
    
def on_connect(client, data, flags, rc):
  for n in nodes:
    print("connected to 'reader/{}/active_tag".format(n.ID))
    client.subscribe('reader/{}/active_tag'.format(n.ID), 1)
    publish.single('reader/{}/status'.format(n.ID), payload=b'read', qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets")

def disconnect(client):
  for n in nodes:
    publish.single('reader/{}/status'.format(n.ID), payload=b'stop', qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets")
  client.disconnect()

#endregion

#region File Handling

def save_file():
  pickle.dump([True, nodes, rfid_tags, logs], open(HANDLER_FILE, mode='wb'))

def save_sheet(service):
  node_vals = list(map(lambda n: [[n.ID], [n.Location]], nodes))
  rfid_tag_vals = list(map(lambda r: [[r.EPC], [str(r.Status)], [r.Owner], [r.Description], [r.Node.Location], [r.Extra]], rfid_tags))
  log_vals = list(map(lambda l: [[l.Timestamp], [str(l.Status)], [l.EPC], [l.Description], [l.Node.Location], [l.Extra]], logs))

  node_resource = {
    "majorDimension": "COLUMNS",
    "values": node_vals
  }

  rfid_tags_resource = {
    "majorDimension": "COLUMNS",
    "values": rfid_tag_vals
  }

  logs_resource = {
    "majorDimension" : "COLUMNS",
    "values" : log_vals
  }

  service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_IDS, range=NODES_RANGE, body=node_resource, valueInputOption="RAW").execute()
  service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_IDS, range=STATUS_RANGE, body=rfid_tags_resource, valueInputOption="RAW").execute()
  service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_IDS, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()

def load_file(data):
  global nodes
  global rfid_tags
  global logs

  obj = pickle.loads(data)

  if obj[0]:
    nodes = obj[1]
    rfid_tags = obj[2]
    logs = obj[3]
    return True
  else:
    return False
  
def load_sheets(service):
  global nodes
  global rfid_tags
  global logs

  # Get nodes from spreadsheet
  node_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=NODES_RANGE).execute().get('values', [])
  nodes = list(map(lambda val: node.Node(val[0], val[1]), node_values))

  # Get status from spreadsheet
  status_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=STATUS_RANGE).execute().get('values', [])
  rfid_tags = list(map(lambda val: rfidtag.RFIDTag(val[0], rfidtag.Status[val[1]], val[2], val[3], next(n for n in nodes if n.Location == str(val[4])), val[5]), status_values))

  # Get logs from spreadsheet
  log_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=LOGS_RANGE).execute().get('values', [])
  logs = list(map(lambda val: log.Log(next(tag for tag in rfid_tags if tag.EPC == val[2]), datetime.datetime.strptime(val[0], "%Y-%m-%dT%H:%M:%S.%fZ"), next(n for n in nodes if n.Location == val[5])), log_values))


#endregion

if __name__ == '__main__':
  # Login to Gsheets service
  creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES) # Generate credentials object from service account file
  service = build('sheets', 'v4', credentials=creds) # Create service object

  rsf_data = None
  try:
    with open(HANDLER_FILE, mode='r+b') as hf:
      rsf_data = hf.read()
  except FileNotFoundError:
    rsf_data = b''
  if rsf_data == b'':
    load_sheets(service)
    save_file()
  else:
    load_file(rsf_data)

  client = mqtt.Client(transport='websockets') # Connect with websockets
  client.on_connect = on_connect
  client.on_message = on_message
  client.connect('broker.hivemq.com', port=8000)

  try:
    client.loop_forever()
  except KeyboardInterrupt:
    save_file()
    disconnect(client)
