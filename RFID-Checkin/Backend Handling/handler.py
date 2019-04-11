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
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import node, log, rfidtag, re, json, pickle, io, datetime, threading, time, queue, enum
from pathlib import Path
from tabulate import tabulate

#TODO: Add documenation for most recent commit 

#region Variable Initialization
SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Read and write permissions for program
SPREADSHEET_ID = '' # Spreadsheet ID for list of ids, names, and clubs

NODES_RANGE = 'readers!a2:c'
STATUS_RANGE = 'ids!a2:f'
LOGS_RANGE = 'log!a2:g'

HANDLER_FILE = 'data/handler.rsf'
LOG_FILE = 'data/logs.csv'
SERVICE_ACCOUNT_FILE = 'data/service_account.json'

DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'

nodes = []
rfid_tags = []
logs = []

service_obj = None
client_obj = None

command_input = True
command_queue = queue.Queue()

node_responses = []
node_responses_lock = threading.Lock()

asu_running = False
cr_running = False

class MQTTResponse(enum.Enum):
  FAILED = 0
  SUCCESSFUL = 1
  ERROR = 2

  def __repr__(self):
    return self.value

  def __str__(self):
    return self.name
#endregion

#region Client Handling

def send_message(topic, msg, timeout = 15, callback = None, 
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

  if not isinstance(timeout, int):
    print(f"Invalid argument type timeout: {timeout}")
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
    command_input = False
    print_out(f"scanned tag with EPC: {js['EPC']}")
    print('Status,Owner,Description,Extra:')
    data = re.sub(r'(?<=,)(\s)', '', command_queue.get()).split(sep=',') # Gets input from command queue, replaces any excess whitespace, splits by commas
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

      print('adding log')
      update_log_file(new_log, 'a')
    save_setup_file()

def on_connect(client, data, flags, rc):
  def ping_node(ind):
    if (ind < len(nodes)):
      send_message(f"reader/{nodes[ind].ID}/status", "ping", timeout=5, callback2=ping_node, args=(ind + 1,))

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
      send_message(f'reader/{nodes[ind].ID}/status', 'stop', timeout=5, print_errors=False, callback=close_readers_stopped, callback2=close_readers_wrapper, args=(ind+1,))
    else:
      client_obj.disconnect()

  print_out(f'attempting to stop nodes: {", ".join(list(map(lambda x: x.ID, nodes)))}')
  close_readers_wrapper(0)
#endregion

#region File Handling
def get_logs(rows):
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
  log_vals = list(map(lambda l: [l.Timestamp.strftime(DATETIME_FORMAT), str(l.Status), l.EPC, l.Owner, l.Description, l.Node.Location, l.Extra], logs))

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
  service_obj.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=NODES_RANGE, body=node_resource, valueInputOption="RAW").execute()
  service_obj.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=STATUS_RANGE, body=rfid_tags_resource, valueInputOption="RAW").execute()
  
  if (log_mode == 'a'):
    service_obj.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()
    logs.clear() # Prevent duplicates being added to the spreadsheet
  elif (log_mode == 'w'):
    service_obj.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()

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
  time_count = 0
   
  print_out('running automatic sheet updates')
  while asu_running:
    if time_count == (24 / updates) * 3600:
      save_sheet(log_mode='a')
      logs.clear()
      time_count = 0

    time_count = time_count + 1
    time.sleep(1)

def print_out(s):
  print(f"{datetime.datetime.now().strftime(DATETIME_FORMAT)}\t{s}")

def command_reader():
  '''
  Starts seperate thread that executes commands read from the standard input.
  '''

  global SPREADSHEET_ID
  global command_input
  global command_queue
  global cr_running

  #region Print Commands
  def show_help(err_msg = ""):
    if not err_msg == "":
      print(f"{err_msg}. Use 'h' for help.")
    else:
      print("""Commands:
exit|x
  Description: Ends handler script
spreadsheet|s [command] -option
  Description: Accesses Google Spreadsheet
  Commands:
    c - ONLY changes current spreadsheet ID. Must specify spreadsheet ID.
      Options:
        SPREADSHEET_ID - Google Sheet ID
    u - Updates Google Spreadsheet with current readers, tags, and logs. Must specify overwrite mode.
      Options:
        a - Append mode will append the logs to the end of the spreadsheet.
        w - Write mode will truncate the current logs and write all current ones.
        x - Doesn't modify the logs sheet at all.
    l - Load spreadsheet and overwrite current readers, tags, and logs.
readers|r -option [ID|message] [message]
  Description: Accesses readers
  Options:
    a - Accesses all readers. Must specify a message.
    i - Acceses a single reader. Must specify a valid reader ID and message.
    d - Directly edit local storage of a node. Must use special arguments afterwards "[ID] [location=''],[status='']". Recommend calling 's u -x' after.
      location - New location for the reader. Leave blank to keep the same.
      status - Must enter either "running" or "stopped". Leave blank to keep the same.
    ID - ID of a reader. Refer to readers!a1:a for reader IDs on spreadsheet.
    Message:
      read - Tells readers to read like normal.
      read_once - Tells readers to read one tag.
      stop - Tells readers to stop reading.
      test_sensors - Tells readers to continuously output sonic sensor reads. Only outputs to readers standard output.
      test_reader - Tells readers to continously output RFID tag reads. Only outputs to readers standard output.
display|d [command] [results]
  Description: Displays data.
  Commands:
    a - Display spreadsheet ID, readers, RFID tags, and logs.
    r - Display RFID tags.
    n - Display readers.
    s - Display spreadsheet ID.
    l - Display logs.
  Results:
    integer, the amount of logs to display (more recent logs have priority)

help|h
  Description: Gets help menu""")

  def print_readers():
    print('\r\nNodes:\r\n')
    node_vals = list(map(lambda v: str(v).split(sep=','), nodes))
    print(tabulate(node_vals, headers=['ID', 'Location', 'Status'], tablefmt="rst"))

  def print_rfids():
    print('\r\nIDs:\r\n')
    rfid_tag_vals = list(map(lambda v: str(v).split(sep=','), rfid_tags))
    print(tabulate(rfid_tag_vals, headers=['EPC', 'Status', 'Owner', 'Description', 'Location', 'Extra'], tablefmt="rst"))

  def print_spreadsheet():
    print('\r\n')
    print(tabulate([[SPREADSHEET_ID]], headers=['Spreadsheet ID'], tablefmt="rst"))

  def print_logs(rows):
    print('\r\nLogs:\r\n')
    log_vals = list(map(lambda v: str(v).split(sep=','), get_logs(rows)))
    print(tabulate(log_vals, headers=['Timestamp', 'Status', 'EPC', 'Owner', 'Description', 'Location', 'Extra'], tablefmt="rst"))

  #endregion
  
  def save_sheet_wrapper(response, topic, msg):
    if response == MQTTResponse.SUCCESSFUL:
      save_sheet(log_mode='x')

  def send_message_wrapper(node_ind, msg, single):
    read_or_stop = msg == 'read' or msg == 'stop'
    if (node_ind < len(nodes)):
      if single:
        if read_or_stop:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=3, callback=save_sheet_wrapper)
        else:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=3)
      else:
        if read_or_stop:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=3, callback=save_sheet_wrapper, callback2=send_message_wrapper, args=(node_ind + 1, msg, single))
        else:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=3, callback2=send_message_wrapper, args=(node_ind + 1, msg, single))

  def read_command():
    while cr_running:
      text = input() # Gets input from standard input
      if text == "":
        continue

      # Handles the scenario in which a different thread needs to use the standard input
      if command_input == False:
        command_queue.put(text)
        continue

      command = re.search(r'^(\w+)(?:\s(?:(\w)(?:\s-?(.+))?|-(\w)\s(\w+)(?:\s(.+))?))?', text, flags=re.MULTILINE)  # Applies regex pattern to input
      
      # Reads commands
      if command.group(1) == 'x' or command.group(1) == 'exit': # Exit command
        break
      elif command.group(1) == 's' or command.group(1) == 'spreadsheet': # Spreadsheet command
        # Handles 'spreadsheet c'
        if command.group(2) == 'c':
          if re.match("^[a-zA-Z0-9-_]+$", command.group(3), flags=re.MULTILINE):
            SPREADSHEET_ID = command.group(3)
          else:
            show_help(f"Invalid spreadsheet ID: '{command.group(3)}'")
        elif command.group(2) == 'u':
          if command.group(3) == 'a' or command.group(3) == 'w' or command.group(3) == 'x':
            save_sheet(log_mode=command.group(3))
          else:
            show_help("Must specify either 'a', 'w', or 'x' for the overwrite mode")
        elif command.group(2) == 'l':
          if input('You might have unsaved data. Are you sure you want to overwrite? (y/n)').capitalize() == 'Y':
            load_sheets()
            save_setup_file()
            update_log_file(logs, 'w')
            logs.clear()
        else:
          show_help(f"Unrecognized argument: {command.group(2)}")
      elif command.group(1) == 'r' or command.group(1) == 'readers':
        if command.group(4) == 'a':
          if command.group(5) == None:
            show_help(f"Must specify a message to send to node(s): {', '.join(list(map(lambda n: n.ID, nodes)))}")
          else:
            send_message_wrapper(0, command.group(5), False)
        elif command.group(4) == 'i':
          if not command.group(5) in list(map(lambda n: n.ID, nodes)):
            show_help(f'Could not find reader: {command.group(5)}')
          else:
            if command.group(6) == None:
              show_help(f"Must specify message to send to: {command.group(5)}")
            else:
              ind = nodes.index(next(n for n in nodes if n.ID == command.group(5)))
              send_message_wrapper(ind, command.group(6), True)
        elif command.group(4) == 'd':
          node_loc = next(n for n in nodes if n.ID == command.group(5))
          loc, stat = command.group(6).split(sep=',')
          if node_loc != None:
            index = nodes.index(node_loc)
            if loc.split(sep=',')[0] != '':
              nodes[index].Location = loc.title()
            if stat.title() == 'Running' or stat.title() == 'Stopped':
              nodes[index].Status = node.Status[stat.title()]
              save_setup_file()
              save_sheet(log_mode='x')
            elif stat != '':
              show_help(f"Unrecognized status: '{stat}'. Status must be either 'Running' or 'Stopped'")
          else:
            show_help('Must specify a node ID.')
        else:
          show_help(f"Unrecognized argument: {command.group(4)}")
      elif command.group(1) == 'd' or command.group(1) == 'display':
        if command.group(2) == 'a':
          print_spreadsheet()
          print_readers()
          print_rfids()
          print_logs(command.group(3))
        elif command.group(2) == 'r':
          print_rfids()
        elif command.group(2) == 'n':
          print_readers()
        elif command.group(2) == 's':
          print_spreadsheet()
        elif command.group(2) == 'l':
          print_logs(command.group(3))
        else:
          show_help(f"Unrecognized argument: '{text}'")
      elif command.group(1) == 'h' or command.group(1) == 'help':
        show_help()
      else:
        show_help(f"Unrecognized commmand: '{text}'")
  
    save_close()
  # Start the thread
  rc_thread = threading.Thread(target=read_command)
  rc_thread.daemon = True
  rc_thread.start()

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
  creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES) # Generate credentials object from service account file
  service_obj = build('sheets', 'v4', credentials=creds) # Create service object
  print_out('logged into Google OAuth')

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