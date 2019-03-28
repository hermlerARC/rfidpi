from googleapiclient.discovery import build
from google.oauth2 import service_account
import paho.mqtt.client as mqtt
import node, log, rfidtag, re, json, io, os

SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Read and write permissions for program
SPREADSHEET_IDS = '1qrFQxaisVqFPFmdBzI8MSJnH-PSuc9i2sePcdpA0_PI' # Spreadsheet ID for list of ids, names, and clubs

NODES_RANGE = 'readers!a2:b'
STATUS_RANGE = 'ids!a2:f'
LOGS_RANGE = 'log!a2:g'

LOG_FILE = 'logs.json'
STATUS_FILE = 'status.json'
SERVICE_ACCOUNT_FILE = 'service_account.json'

nodes = []
rfid_tags = []
logs = []

log_stream = None
status_stream = None

def readTag(e):
    for x in e:
        epc = str(x.epc, 'utf-8')
        if not any(j[0][0] == epc for j in IDS):
            name = input('%s\tName: '%(epc))
            item = input('%s\tItem: '%(epc))
            row = [[epc], ["%s.%s"%(name,item)], ["in"]]
            IDS.append(row)

            resource = {
                "majorDimension": "COLUMNS",
                "values": row # Creates row object formatted as: Time, Name, ID, Club
            }
            
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_IDS,
                range=RANGE_IDS,
                body=resource,
                valueInputOption="RAW"
            ).execute() # Append new line to LOG sheet 

def update_sheet(service):
  node_vals = []
  rfid_tag_vals = []
  log_vals = []

  for n in node:
    node_vals.append([[n.ID], [n.Location]])

  for r in rfid_tags:
    rfid_tag_vals.append([[r.EPC], [str(r.Status)], [r.Owner], [r.Description], [r.Node.Location], [r.Extra]])

  for l in logs:
    log_vals.append([[l.Timestamp], [str(l.Status)], [l.EPC], [l.Description], [l.Node.Location], [l.Extra]])

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

def on_message(client, data, msg):
  curr_node = next(n for n in nodes if n.id == re.search('\/(.+)\/', msg.topic).group(1))
  js = json.load(str(msg.payload, 'utf-8'))
  
  for item in js:
    l = log.Log(curr_node, item)

  with open(LOG_FILE, mode='a') as logf:
    pass
    
def on_connect(client, data, flags, rc):
  for n in NODES:
    client.subscribe('reader/{}/status'.format(n.id), 1)

if __name__ == '__main__':
  # Login to Gsheets service
  creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES) # Generate credentials object from service account file
  service = build('sheets', 'v4', credentials=creds) # Create service object

  # Get nodes from spreadsheet
  node_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=NODES_RANGE).execute().get('values', [])
  nodes = list(map(lambda val: node.Node(val[0], val[1]), node_values))

  # Get status from spreadsheet
  status_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=STATUS_RANGE).execute().get('values', [])
  rfid_tags = list(map(lambda val: rfidtag.RFIDTag(val[0], rfidtag.Status[val[1]], val[2], val[3], next(n for n in nodes if n.Location == str(val[4])), val[5]), status_values))

  # Get logs from spreadsheet
  log_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=LOGS_RANGE).execute().get('values', [])
  logs  = list(map(lambda val: log.Log(next(tag for tag in rfid_tags if tag.EPC == val[2]), val[0], next(n for n in nodes if n.Location == val[5])), log_values))

  exit()
  client = mqtt.Client(transport='websockets') # Connect with websockets
  client.on_connect = on_connect
  client.on_message = on_message
  client.connect('broker.hivemq.com', port=8000)

  client.loop_forever()

