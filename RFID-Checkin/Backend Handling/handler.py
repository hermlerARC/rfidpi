'''
RFID Logging Software

Description (handler.py): 
Handles the receiving and logging of tag reads from all nodes and submitting to GSheets and local database.

Contributors:
Dom Stepek, Gavin Furlong

To read more about the Google API, go to : https://developers.google.com/identity/protocols/OAuth2
To read more about MQTT for Python, go to: https://pypi.org/project/paho-mqtt/
To read more about Mercury API for Python, go to: https://github.com/gotthardp/python-mercuryapi

Edited on: March 29, 2019
'''

from googleapiclient.discovery import build
from google.oauth2 import service_account
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import node, log, rfidtag, re, json, pickle, io, datetime, threading, time, atexit

#region Variable Initialization
SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Read and write permissions for program
SPREADSHEET_ID = '' # Spreadsheet ID for list of ids, names, and clubs

NODES_RANGE = 'readers!a2:b'
STATUS_RANGE = 'ids!a2:f'
LOGS_RANGE = 'log!a2:g'

HANDLER_FILE = 'data/handler.rsf'
LOG_FILE = 'data/logs.csv'
SERVICE_ACCOUNT_FILE = 'data/service_account.json'

nodes = []
rfid_tags = []
logs = []

log_stream = None
status_stream = None

sheet_update_running = False
#endregion

#region Client Handling
def on_message(client, data, msg):
  '''
  Appends new logs from the JSON file received.

  Unpacks the data (in JSON format) into a Python object, finds out which node the message came from,
  creates a new log object, updates the rfid tags list with new log data, and appends the log
  object to the log file.
    
  Args:
    client: client, the client instance for this callback
    data: string, userdata on the call
    message: an instance of MQTTMessage. This is a class with members topic, payload, qos, retain. Formatted as follows:\n
      [
        {
            "EPC": {epc},
            "Time": {timestamp},
            "Status": {status of tag},
            "RSSI": {strength of the tag signal}
        },
        ...
      ]
  '''

  js = json.loads(str(msg.payload, 'utf-8')) # Deserialize JSON object to Python Object to allow for manipulation
  curr_node = next(n for n in nodes if n.ID == re.search('\/(.+)\/', msg.topic).group(1)) # Find out which unit this call came from

  for item in js: 
    curr_tag_index = rfid_tags.index(next(t for t in rfid_tags if t.EPC == item['EPC'])) # Get index of the RFID tag associated with the log
    
    if curr_tag_index == -1:
      continue

    rfid_tags[curr_tag_index].Node = curr_node # Update the tag's current Node
    rfid_tags[curr_tag_index].Status = rfidtag.Status(item['Status']) # Update the tag's status

    # Create the new log object and add it to the database
    new_log = log.Log(rfid_tags[curr_tag_index], datetime.datetime.strptime(item['Time'], "%Y-%m-%dT%H:%M:%S.%f"), curr_node)
    logs.append(new_log)

    update_log_file(new_log, 'a')
    save_setup_file()

  print_out(f'received message from {curr_node.ID}')

def on_connect(client, data, flags, rc):
  # Connects to every Node
  for n in nodes:
    client.subscribe('reader/{}/active_tag'.format(n.ID), 1) # Listener for updates on 'reader/{n.ID}/active_tag' topic
    publish.single('reader/{}/status'.format(n.ID), payload=b'read', qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets") # Tell all readers to begin reading

  print_out(f'connected to {", ".join(list(map(lambda n: n.ID, nodes)))}')

def disconnect(client):
  '''
  Tells all nodes to stop reading and disconnects the MQTT client.

  Args:
    client: client, the client object generated by MQTT library.
  '''

  # Sends every Node a 'stop' message.
  for n in nodes:
    publish.single('reader/{}/status'.format(n.ID), payload=b'stop', qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets")
  client.disconnect()
  
  print_out('disconnecting client')
#endregion

#region File Handling
def update_log_file(l, write_mode = 'a'):
  '''
  Appends to the log file a new instance.

  Args:
    l: Log or list<log.Log>, the log object or list of log objects to be appended.
    write_mode: string, tells function whether it should append or rewrite all logs. Options:\n
      a: Append mode, adds log values to the end of the file.
      w: Write mode, truncates log values in file and writes logs.
  '''

  if isinstance(l, log.Log):
    with open(LOG_FILE, mode='a') as hf:
      hf.write('\n' + repr(l))
  elif isinstance(l, list):
    if (write_mode == 'a'):
      with open(LOG_FILE, mode='a') as hf:
        for i in l:
          hf.write('\n' + repr(i))
    elif (write_mode == 'w'):
      with open(LOG_FILE, mode='w') as hf:
        hf.write("Timestamp,Status,EPC,Owner,Description,Location,Extra")
        for i in l:
          hf.write('\n' + repr(i))

  print_out(f'updated {LOG_FILE}')

def save_setup_file():
  '''
  Saves the current nodes and RFID tags into the handler file.
  '''

  # Creates wrapper of the data generated from the nodes, rfid_tags, and logs lists, pickles, and saves to HANDLER_FILE
  pickle.dump([SPREADSHEET_ID, nodes, rfid_tags], open(HANDLER_FILE, mode='wb'))

  print_out(f'updated {HANDLER_FILE}')

def save_sheet(service, log_mode = 'a'):
  '''
  Updates the spreadsheet with current values inside of nodes, rfid_tags, and logs

  Args:
    service: resource, object generated by the GOAuth API 
    log_mode: string, represents whether the sheet should append the logs or rewrite them. Options:\n
      a: Append mode, adds log values to existing ones.
      w: Write mode, truncates sheets log values and writes new ones.
  '''

  # GSheets API wants an array of values, so we create a series of the following object associated with all nodes, rfid tags, and logs
  # [
  #   [
  #     val_0_0, val_0_1, ...
  #   ],
  #   [
  #     val_1_0, val_1_1, ...
  #   ],
  #   ....
  # ]
  node_vals = list(map(lambda n: [n.ID, n.Location], nodes))
  rfid_tag_vals = list(map(lambda r: [r.EPC, str(r.Status), r.Owner, r.Description, r.Node.Location, r.Extra], rfid_tags))
  log_vals = list(map(lambda l: [l.Timestamp.strftime("%d/%m/%Y %H:%M:%S"), str(l.Status), l.EPC, l.Owner, l.Description, l.Node.Location, l.Extra], logs))

  # Tell GSheets that we want to it to post our data by column
  node_resource = {
    "majorDimension": "ROWS",
    "values": node_vals
  }

  rfid_tags_resource = {
    "majorDimension": "ROWS",
    "values": rfid_tag_vals
  }

  logs_resource = {
    "majorDimension" : "ROWS",
    "values" : log_vals
  }

  # Send GSheets to execute update request with RAW input (meaning GSheets will not perform any 
  # extra formatting on the data. This prevents the program from having to understand multiple formats).
  service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=NODES_RANGE, body=node_resource, valueInputOption="RAW").execute()
  service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=STATUS_RANGE, body=rfid_tags_resource, valueInputOption="RAW").execute()
  
  if (log_mode == 'a'):
    service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()
  elif (log_mode == 'w'):
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()

  print_out(f'saved data to {SPREADSHEET_ID} sheet')

def load_setup_file(data):
  '''
  Loads nodes and rfid tags from the unpickled data.

  Args:
    data: string, text read from the setup file. Should be formatted as follows:\n
          [List<node.Node>, List<rfidtag.RFIDTag>]
  '''

  global nodes
  global rfid_tags
  global SPREADSHEET_ID

  obj = pickle.loads(data)

  SPREADSHEET_ID = obj[0]
  nodes = obj[1]
  rfid_tags = obj[2]

  print_out(f'loaded {HANDLER_FILE} file')
  
def load_sheets(service):
  '''
  Retrieves nodes, rfid tags, and logs from the spreadsheet.

  Args:
    service: resource, object generated by the GOAuth API
  '''

  global nodes
  global rfid_tags
  global logs

  # Get nodes from spreadsheet
  node_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=NODES_RANGE).execute().get('values', [])
  nodes = list(map(lambda val: node.Node(val[0], val[1]), node_values))

  # Get status from spreadsheet
  status_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=STATUS_RANGE).execute().get('values', [])
  rfid_tags = list(map(lambda val: rfidtag.RFIDTag(val[0], rfidtag.Status[val[1]], val[2], val[3], next(n for n in nodes if n.Location == str(val[4])), val[5]), status_values))

  # Get logs from spreadsheet
  log_values = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE).execute().get('values', [])
  logs = list(map(lambda val: log.Log(next(tag for tag in rfid_tags if tag.EPC == val[2]), datetime.datetime.strptime(val[0], "%d/%m/%Y %H:%M:%S"), next(n for n in nodes if n.Location == val[5])), log_values))

  print_out(f'loaded from {SPREADSHEET_ID} sheet')

#endregion

def automatic_sheet_update(service, updates = 6):
  '''
  Updates the GSheets file periodically

  Args:
    service: resource, object generated by the GOAuth API
    update: int, amount of sheet updates per day.
  '''
  time_count = 0
   
  print_out('running automatic sheet updates')
  while sheet_update_running:
    if time_count == (24 / updates) * 3600:
      save_sheet(service, log_mode='a')
      logs.clear()
      time_count = 0

    time_count += 1
    time.sleep(1)

def print_out(s):
  print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\t{s}")

def exiting(client):
  '''
  Closes script, saves files, and disconnects the client.

  Args:
    client: client, the client instance for this callback
  '''

  global sheet_update_running
  sheet_update_running = False
  save_setup_file()
  disconnect(client)
  print_out('Stopping handler...')
  exit()

def command_reader(client, service):
  global SPREADSHEET_ID

  #region Print Commands
  def show_help(err_msg = ""):
    if not err_msg == "":
      print(err_msg)

    print("""Commands:
      x
        Description: Ends handler script
      s [command] -option
        Description: Accesses Google Spreadsheet
        Commands:
          c - ONLY changes current spreadsheet ID. Must specify spreadsheet ID.
            Options:
              SPREADSHEET_ID - Google Sheet ID
          u - Updates Google Spreadsheet with current readers, tags, and logs. Must specify overwrite mode.
            Options:
              a - Append mode will append the logs to the end of the spreadsheet.
              w - Write mode will truncate the current logs and write all current ones.
          l - Load spreadsheet and overwrite current readers, tags, and logs.
      r -option [ID|message] [message]
        Description: Accesses readers
        Options:
          a - Accesses all readers. Must specify a message.
          s - Acceses a single reader. Must specify a valid reader ID and message.
          ID - ID of a reader. Refer to readers!a1:a for reader IDs on spreadsheet.
          Message:
            read - Tells readers to read like normal.
            read_once - Tells readers to read one tag.
            stop - Tells readers to stop reading.
            test_sensors - Tells readers to continuously output sonic sensor reads. Only outputs to readers standard output.
            test_reader - Tells readers to continously output RFID tag reads. Only outputs to readers standard output.
      d [command]
        Description: Displays data.
        Commands:
          a - Display spreadsheet ID, readers, RFID tags, and logs.
          r - Display RFID tags.
          n - Display readers.
          s - Display spreadsheet ID.
          l - Display logs.
      h
        Description: Gets help menu""")

  def print_readers():
    print("Nodes:\nID\tLocation")
    for x in nodes:
      print(x)

  def print_rfids():
    print("Registered Tags:\nEPC\tStatus\tOwner\tDescription\tLocation\tExtra")
    for x in rfid_tags:
      print(x)

  def print_spreadsheet():
    print(f"Spreadsheet ID: {SPREADSHEET_ID}")

  def print_logs():
    print("Logs:\nTimestamp\tStatus\tEPC\tOwner\tDescription\tLocation\tExtra")
    for x in logs:
      print(x)
  #endregion

  def read_command():
    while True:
      text = input()
      command = re.search('^(\w)(?:\s(?:(\w)(?:\s-?(.+))?|-(\w)\s(\w+)(?:\s(\w+))?))?', text, flags=re.MULTILINE) 
      
      if command.group(1) == 'x':
        break
      elif command.group(1) == 's':
        if command.group(2) == 'c':
          SPREADSHEET_ID = command.group(3)
        elif command.group(2) == 'u':
          if command.group(3) == 'a' or command.group(3) == 'w':
            save_sheet(service, log_mode=command.group(3))
          else:
            show_help('Must specify either "a" or "w" for the overwrite mode')
        elif command.group(2) == 'l':
          if input('You might have unsaved data. Are you sure you want to overwrite? (y/n)').capitalize() == 'Y':
            load_sheets(service)
            save_setup_file()
            update_log_file(logs, 'w')
            logs.clear()
        else:
          show_help(f"Unrecognized argument: {command.group(2)}")
      elif command.group(1) == 'r':
        if command.group(4) == 'a':
          if command.group(5) == None:
            show_help(f"Must specify a message to send to {', '.join(list(map(lambda n: n.ID, nodes)))}.")
          for n in nodes:
            publish.single('reader/{}/status'.format(n.ID), payload=bytes(command.group(5)), qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets")
        elif command.group(4) == 'i':
          if not command.group(5) in list(map(lambda n: n.ID, nodes)):
            show_help(f'Could not find reader {command.group(5)}.')
          else:
            if command.group(6) == None:
              show_help(f"Must specify message to send to {command.group(5)}")
            else:
              publish.single('reader/{}/status'.format(command.group(5)), payload=bytes(command.group(6)), qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets")
        else:
          show_help(f"Unrecognized argument: {command.group(4)}")
      elif command.group(1) == 'd':
        if command.group(2) == 'a':
          print_spreadsheet()
          print_readers()
          print_rfids()
          print_logs()
        elif command.group(2) == 'r':
          print_rfids()
        elif command.group(2) == 'n':
          print_readers()
        elif command.group(2) == 's':
          print_spreadsheet()
        elif command.group(2) == 'l':
          print_logs()
        else:
          show_help(f"Unrecognized argument: {command.group(2)}")
      elif command.group(1) == 'h':
        show_help()
      else:
        show_help(f"Unrecognized commmand: {text}")
    exiting(client)
  threading.Thread(target=read_command).start()

if __name__ == '__main__':
  '''
  Setup for the handling of the tags received from each Node.
  
  Logs into GOAuth, opens and reads data files, starts automatic sheet update service, creates MQTT client.
  Catches KeyboardInterrupt to kill the program safely
  '''

  # Login to GSheets service
  creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES) # Generate credentials object from service account file
  service = build('sheets', 'v4', credentials=creds) # Create service object
  print_out('logged into Google OAuth')

  rsf_data = None
  csv_data = None
  # Attempts to open the handler and log file, creating the file if need be.
  with open(HANDLER_FILE, mode='r+b') as hf:
    rsf_data = hf.read()
  with open(LOG_FILE, mode='r+') as lf:
    csv_data = lf.read(1)
    if (csv_data == ''):
      lf.write("Timestamp,Status,EPC,Owner,Description,Location,Extra")

  # If the handler file is empty, pull data from GSheets, otherwise use data stored locally
  if rsf_data == b'':
    SPREADSHEET_ID = input('Enter spreadsheet ID: ')
    load_sheets(service)
    save_setup_file()
    update_log_file(logs, 'w')
    logs.clear()
  else:
    load_setup_file(rsf_data)
    
  sheet_update_running = True
  threading.Thread(target=automatic_sheet_update, args=(service, 6)).start()

  client = mqtt.Client(transport='websockets') # Connect with websockets
  client.on_connect = on_connect
  client.on_message = on_message
  client.connect('broker.hivemq.com', port=8000)

  try:
    command_reader(client, service)
    client.loop_forever()
  except KeyboardInterrupt:
    exiting(client)