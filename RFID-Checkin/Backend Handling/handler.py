'''
RFID Logging Software

Description (handler.py): 
Handles the receiving and logging of tag reads from all nodes and submitting to GSheets and local database.

Contributors:
Dom Stepek, Gavin Furlong, Ryan Hermle, Abdullah Shabir

To read more about the Google API, go to : https://developers.google.com/identity/protocols/OAuth2
To read more about MQTT for Python, go to: https://pypi.org/project/paho-mqtt/
To read more about Mercury API for Python, go to: https://github.com/gotthardp/python-mercuryapi

Edited on: April 4, 2019
'''
from googleapiclient.discovery import build
from google.oauth2 import service_account
from node import Node
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import log, rfidtag, re, json, pickle, io, datetime, threading, time, queue, enum
from pathlib import Path
from tabulate import tabulate

class Handler:
  def __init__(self):
    self.__SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    self.__NODES_RANGE = "readers!a2:c"
    self.__RFIDTAGS_RANGE = "ids!a2:f"
    self.__LOGS_RANGE = "log!a2:g"

    self.__SETTINGS_FILE = "data/settings.rsf"
    self.__LOG_FILE = "data/logs.csv"
    self.__SERVICE_ACC_FILE = "data/service_account.json"

    self.__DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"

    self.__spreadsheetID = ""
    self.__sheets_update_interval = 6

    self.__nodes = []
    self.__rfidtags = []
    self.__new_logs = []

    self.__automatic_sheets_update_running = False

    self.__google_service = None

    self.__google_login()

    Path(self.__SETTINGS_FILE).touch()
    Path(self.__LOG_FILE).touch()

  def __google_login(self):
    creds = service_account.Credentials.from_service_account_file(self.__SERVICE_ACC_FILE, scopes=self.__SCOPES) # Generate credentials object from service account file
    self.__google_service = build('sheets', 'v4', credentials=creds) # Create service object

  def __load_settings_file(self):
    rsf_data = None

    with open(self.__SETTINGS_FILE, 'r+b') as sf:
      rsf_data = sf.read()

    settings_obj = pickle.loads(rsf_data)
    self.__spreadsheetID = settings_obj['spreadsheet_id']
    self.__rfidtags = settings_obj['rfid_tags']
    
    self.__shutdown_nodes()
    nodes = settings_obj['nodes']
    for node in nodes:
      new_node = Node(node['id'], node['location'])
      if node['node_status']

  def __save_settings_file(self):
    node_properties = list(map(lambda node: {'id' : node.GetID(), 'location' : node.GetLocation(), 'node_status' : node.GetNodeStatus(), 'log_status' : node.GetLogStatus()}, self.__nodes))
    
    pickle.dump({
      'spreadsheet_id' : self.__spreadsheetID,
      'rfid_tags' : self.__rfidtags,
      'nodes' : node_properties
    }, open(self.__SETTINGS_FILE, mode='wb'))

  def __shutdown_nodes(self):
    for node in self.__nodes:
      node.Shutdown()

#region Client Handling

def send_message(topic, msg, timeout = None, callback = None, 
  print_errors = True, callback2 = None, args=()): 
  """
  Posts a single message to the topic, waits for a response, and returns a status code.

  Args:
    topic: str, the MQTT topic to post the message. Ex: 'reader/12345/active_tag'
    msg: bytes, data that will be posted to the topic.
    timeout: int, seconds to wait a message to be received.
    callback: function, called with args: MQTTResponse, node, and msg.
    callback2: function, called after receiving a response.
    args: tuple, arguments to callback2 is called with.
  """
  global node_responses
  global node_responses_lock

  def print_response(response, node, msg):
    print_out(f"Received response code {response.value}: {str(response)} after sending '{msg}' to '{node}'")

  def run():
    # Send message
    curr_time = datetime.datetime.now()

    topic_node = re.search(r'reader\/(.+)\/.+', topic).group(1)
    publish.single(topic, payload=msg, qos=1, hostname="broker.hivemq.com", port=8000, transport="websockets")
    response = {"node": topic_node, "msg" : msg}
    server_response = MQTTResponse.FAILED
    
    # Receive node response
    while (datetime.datetime.now() - curr_time).total_seconds() <= timeout and server_response == MQTTResponse.FAILED:
        node_responses_lock.acquire()

        if response in node_responses:
          server_response = MQTTResponse.SUCCESSFUL
          node_responses.remove(response)
        
        node_responses_lock.release()
    
    # Check to see the response matches the message sent
    if hasattr(callback, '__call__'):
      callback(server_response, topic_node, msg)
    if hasattr(callback2, '__call__'):
      callback2(*args)
    if print_errors and server_response == MQTTResponse.FAILED:
      print_response(MQTTResponse.FAILED, topic_node, msg)

  if timeout == None:
    timeout = DEFAULT_MESSAGE_TIMEOUT
  if not isinstance(timeout, float):
    print(f"Invalid argument type timeout: '{timeout}'. Using default timeout '{DEFAULT_MESSAGE_TIMEOUT}' instead.")
    raise ValueError
  if timeout <= 0:
    print(f"timeout must be greater than 0")
    raise ValueError

  run_thread = threading.Thread(target=run)
  run_thread.daemon = True
  run_thread.start()
  
def on_message(client, data, msg):
  '''
  Appends new logs from the JSON file received.

  Unpacks the data (in JSON format) into a Python object, determines the node which sent the message,
  creates a new log object, updates the rfid tags list with new log data, and appends the log
  object to the log file.
    
  Args:
    client: client, the client instance for this callback
    data: string, userdata on the call
    message: an instance of MQTTMessage. This is a class with members topic, payload, qos, retain.\n
    Formatted as follows on active_tag topic:\n
      [
        {
            "EPC" : {epc},
            "Time" : {timestamp},
            "Status" : {status of tag},
            "RSSI" : {strength of the tag signal}
        },
        ...
      ]\n
    Formatted as follows on response topic:\n
      {
        "MESSAGE" : {response}
      }
  '''

  global command_input
  global command_queue
  global node_responses
  global node_responses_lock

  js = json.loads(str(msg.payload, 'utf-8')) # Deserialize JSON object to Python Object to allow for manipulation
  curr_node = next(n for n in nodes if n.ID == re.search(r'\/(.+)\/', msg.topic).group(1)) # Find out which unit this call came from
  topic = re.search(r'reader\/.+\/(\w+)', msg.topic).group(1)

  if topic == 'response':
    if js['MESSAGE'] == 'ping':
      print_out(f'connected to {curr_node.ID}')
    elif js['MESSAGE'] == 'err':
      print_out(f"{curr_node.ID} error {js['CODE']}: {node.ErrorCode[int(js['CODE'], 16)]}")
    else:
      if js['MESSAGE'] == 'read':
        nodes[nodes.index(curr_node)].Status = node.Status.Running
        save_setup_file()
      elif js['MESSAGE'] == 'stop':
        nodes[nodes.index(curr_node)].Status = node.Status.Stopped
        save_setup_file()
    
    node_responses_lock.acquire()
    node_responses.append({
      'node' : curr_node.ID,
      'msg' : js['MESSAGE']
    })

    node_responses_lock.release()

  elif topic == 'scanned':
    if js['EPC'] in list(map(lambda x: x.EPC, rfid_tags)):
      print(f"ERROR: Attempted to reassign an existing tag '{js['EPC']}''")
      return

    command_input = False
    print_out(f"scanned tag with EPC: {js['EPC']}")
    print('Status,Owner,Description,Extra:')
    response = command_queue.get()
    
    if not re.match(r'(.+,){3}\s?([\S]+)', response):
      print("ERROR: Must have 4 fields seperated by a ',' character.")
      command_input = True
      return

    status, owner, description, extra = re.sub(r'(?<=,)(\s)', '', response).split(sep=',') # Gets input from command queue, replaces any excess whitespace, splits by commas
    command_input = True

    new_tag = rfidtag.RFIDTag(js['EPC'], rfidtag.Status[data[0].title()], data[1].title(), data[2].title(), curr_node, data[3].title())
    rfid_tags.append(new_tag)
    save_setup_file()
  elif topic == 'active_tag':
    for item in js: 
      curr_tag_index = rfid_tags.index(next(t for t in rfid_tags if t.EPC == item['EPC'])) # Get index of the RFID tag associated with the log
      
      if curr_tag_index == -1:
        continue
      rfid_tags[curr_tag_index].Node = curr_node # Update the tag's current Node
      rfid_tags[curr_tag_index].Status = rfidtag.Status(item['Status']) # Update the tag's status

      # Create the new log object and add it to the database
      new_log = log.convert_to_log(rfid_tags[curr_tag_index], datetime.datetime.strptime(item['Time'], DATETIME_FORMAT), curr_node)
      logs.append(new_log)

      update_log_file(new_log, 'a')
    save_setup_file()

def on_connect(client, data, flags, rc):
  def ping_node(ind):
    if (ind < len(nodes)):
      send_message(f"reader/{nodes[ind].ID}/status", "ping", timeout=float(2), callback2=ping_node, args=(ind + 1,))

  print_out(f'connecting to nodes: {", ".join(list(map(lambda x: x.ID, nodes)))}')
  # Connects to every Node
  for n in nodes:
    client.subscribe(f'reader/{n.ID}/active_tag', 1) # Listener for tag reads
    client.subscribe(f'reader/{n.ID}/scanned', 1) # Listener for single scans
    client.subscribe(f'reader/{n.ID}/response', 1) # Listener for response
  ping_node(0)

def shutdown_nodes():
  '''
  Tells all nodes to stop reading and disconnects the MQTT client.
  '''
  global client_obj

  def close_readers_stopped(rep, n, msg):
    print_out(f"stopped node: {n}" if rep == MQTTResponse.SUCCESSFUL else f"failed to stop: {n}")

  def close_readers_wrapper(ind):
    if (ind < len(nodes)):
      send_message(f'reader/{nodes[ind].ID}/status', 'stop', timeout=float(5), print_errors=False, callback=close_readers_stopped, callback2=close_readers_wrapper, args=(ind+1,))
    else:
      client_obj.disconnect()

  print_out(f'attempting to stop nodes: {", ".join(list(map(lambda x: x.ID, nodes)))}')
  close_readers_wrapper(0)
#endregion

#region File Handling
def get_logs(rows = None):
  '''
  Retreives a list of logs from the LOGS_FILE with specified rows.

  Args:
    rows: int, max amount of rows to retrieve (most recent logs have priority).
  '''
  global nodes

  logs = []
  count = 0
  with open(LOG_FILE, mode='r') as lf:
    for l in lf:

      # Skips header
      if count == 0: 
        count += 1
        continue

      logs.append(log.convert_to_log(l, nodes))
  return logs if rows == None else logs[-int(rows):]

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
  global SPREADSHEET_ID
  global nodes
  global rfid_tags

  # Creates wrapper of the data generated from the nodes, rfid_tags, and logs lists, pickles, and saves to HANDLER_FILE
  pickle.dump([SPREADSHEET_ID, nodes, rfid_tags], open(HANDLER_FILE, mode='wb'))

  print_out(f'updated {HANDLER_FILE}')

def save_sheet(log_mode = 'a'):
  '''
  Updates the spreadsheet with current values inside of nodes, rfid_tags, and logs

  Args:
    log_mode: string, represents whether the sheet should append the logs or rewrite them. Options:\n
      a: Append mode, adds log values to existing ones.
      w: Write mode, truncates sheets log values and writes new ones.
      x: Skip mode, updates the node and RFID sheets and not the log sheet.
  '''
  global service_obj

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

  node_vals = list(map(lambda n: [n.ID, n.Location, str(n.Status)], nodes))
  rfid_tag_vals = list(map(lambda r: [r.EPC, str(r.Status), r.Owner, r.Description, r.Node.Location, r.Extra], rfid_tags))

  log_vals = []
  if log_mode == 'a':
    log_vals = list(map(lambda l: [l.Timestamp.strftime(DATETIME_FORMAT), str(l.Status), l.EPC, l.Owner, l.Description, l.Node.Location, l.Extra], logs))
  elif log_mode == 'w':
    log_vals = list(map(lambda l: [l.Timestamp.strftime(DATETIME_FORMAT), str(l.Status), l.EPC, l.Owner, l.Description, l.Node.Location, l.Extra], get_logs()))
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
  while True:
    try:
      service_obj.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=NODES_RANGE, body=node_resource, valueInputOption="RAW").execute()
      service_obj.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=STATUS_RANGE, body=rfid_tags_resource, valueInputOption="RAW").execute()
      
      if (log_mode == 'a'):
        service_obj.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()
        logs.clear() # Prevent duplicates being added to the spreadsheet
      elif (log_mode == 'w'):
        service_obj.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()
      break
    except ConnectionResetError:
      print_out('reconnecting to Google API')
      establish_google_conn()

  print_out(f'saved data to {SPREADSHEET_ID} spreadsheet')

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
  
def load_sheets():
  '''
  Retrieves nodes, rfid tags, and logs from the spreadsheet.
  '''

  global nodes
  global rfid_tags
  global logs
  global service_obj

  # Get nodes from spreadsheet
  node_values = service_obj.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=NODES_RANGE).execute().get('values', [])
  nodes = list(map(lambda val: node.Node(val[0], val[1], val[2]), node_values))

  # Get status from spreadsheet
  status_values = service_obj.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=STATUS_RANGE).execute().get('values', [])
  rfid_tags = list(map(lambda val: rfidtag.RFIDTag(val[0], rfidtag.Status[val[1]], val[2], val[3], next(n for n in nodes if n.Location == str(val[4])), val[5]), status_values))

  # Get logs from spreadsheet
  log_values = service_obj.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE).execute().get('values', [])
  logs = list(map(lambda val: log.convert_to_log(','.join(val), nodes), log_values))

  print_out(f'loaded from {SPREADSHEET_ID} sheet')

#endregion

#region Miscellaneous
def automatic_sheet_update(updates = 6):
  '''
  Updates the GSheets file periodically

  Args:
    update: int, amount of sheet updates per day.
  '''
  global asu_running
  global sheet_updates_interval

  sheet_updates_interval = updates
  time_count = 0
   
  print_out('running automatic sheet updates')
  while asu_running:
    if time_count == (24 / sheet_updates_interval) * 3600:
      save_sheet(log_mode='a')
      logs.clear()
      time_count = 0

    time_count = time_count + 1
    time.sleep(1)

def print_out(s):
  print(f"{datetime.datetime.now().strftime(DATETIME_FORMAT)}\t{s}")

def save_close():
  global asu_running
  global cr_running

  cr_running = False
  asu_running = False
  shutdown_nodes()

#endregion

if __name__ == '__main__':
  '''
  Setup for the handling of the tags received from each Node.
  
  Logs into GOAuth, opens and reads data files, starts automatic sheet update service, creates MQTT client.
  Catches KeyboardInterrupt to kill the program safely
  '''
  # Login to GSheets service
  print_out('starting handler.py...')
  establish_google_conn()

  rsf_data = None
  csv_data = None

  # Attempts to open the handler and log file, creating the file if need be.
  Path(HANDLER_FILE).touch()
  Path(LOG_FILE).touch()

  # Get setup data from HANDLER_FILE
  with open(HANDLER_FILE, mode='r+b') as hf:
    rsf_data = hf.read()

  # Check to see if LOG_FILE has any data in it and if it doesn't, add a header.
  with open(LOG_FILE, mode='r+') as lf:
    csv_data = lf.read(1)
    if (csv_data == ''):
      lf.write("Timestamp,Status,EPC,Owner,Description,Location,Extra")

  # If the handler file is empty, pull data from GSheets, otherwise use data stored locally
  if rsf_data == b'':
    SPREADSHEET_ID = input('Enter spreadsheet ID: ')
    load_sheets()
    save_setup_file()
    update_log_file(logs, 'w')
    logs.clear()
  else:
    load_setup_file(rsf_data)
    
  # Create a new thread to handle the automatic sheet updates
  asu_running = True
  asu_thread = threading.Thread(target=automatic_sheet_update, args=(6,))
  asu_thread.daemon = True
  asu_thread.start()

  # Setup client_obj
  client_obj = mqtt.Client(transport='websockets') # Connect with websockets
  client_obj.on_connect = on_connect
  client_obj.on_message = on_message
  client_obj.connect('broker.hivemq.com', port=8000)

  try:
    cr_running = True
    command_reader() # Start command reading thread
    client_obj.loop_forever() # Automatically handle reconnecting to the MQTT client in case of timeout.
  except KeyboardInterrupt:
    print('\r\nERROR: Data can be corrupted in the Google Sheets spreadsheet.\nClose script using the command "exit" next time.\nUpon reopening the script, run the command "s u -x".')

  save_setup_file()
  update_log_file(logs, write_mode='a')
  save_sheet(log_mode='a')
  print_out('closed handler.py')