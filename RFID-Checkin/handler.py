'''
RFID Logging Software

Description (handler.py): 
Handles the receiving and logging of tag reads from all nodes and submitting to GSheets and local database.

Contributors:
Dom Stepek

To read more about the Google API, go to : https://developers.google.com/identity/protocols/OAuth2
To read more about MQTT for Python, go to: https://pypi.org/project/paho-mqtt/
To read more about Mercury API for Python, go to: https://github.com/gotthardp/python-mercuryapi

Edited on: May 4, 2019
'''
from googleapiclient.discovery import build
from google.oauth2 import service_account
from node import Node, Status
from log import Log
from rfidtag import RFIDTag
from command_reader import CommandReader
from pathlib import Path
from node_enums import Command
import re, asyncio, threading, queue, datetime, pickle, time

class Handler:
  def __init__(self):
    # Setup variables for Google Sheets API
    self.__SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    self.__NODES_RANGE = "readers!a2:c"
    self.__RFIDTAGS_RANGE = "ids!a2:f"
    self.__LOGS_RANGE = "log!a2:g"

    # Setup files for server
    self.__SETTINGS_FILE = "data/settings.rsf"
    self.__LOG_FILE = "data/logs.csv"
    self.__SERVICE_ACC_FILE = "data/service_account.json"

    self.__DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"
    
    self.__spreadsheetID = ""

    self.__nodes = []
    self.__rfidtags = []
    self.__log_buffer = [] # Does not actually contain every log. Only new logs that aren't added to the spreadsheet

    print("Frontend for RFID Logging Software.\r\n\r\nHandles data from nodes and stores data locally, while occasionally pushing the data to a Google spreadsheet.\r\nThis softare is intended as a direct complement to the node(s).\r\n\r\nDeveloped at American River College\r\nWritten by: Dominique Stepek")
    self.__command_reader = CommandReader(self)

    self.__google_service = None
    self.__google_login()

    self.LoadSettingsFile()

    self.__sheets_update_interval_queue = queue.Queue()
    self.__sheets_update_interval_queue.put(6) # Amount of updates per day
    self.__automatic_sheets_update_running = True
    threading.Thread(target=self.__start_automatic_sheet_update_service).start()
    self.__command_reader.Start()
    
  @property
  def SpreadSheetID(self):
    return self.__spreadsheetID

  @property
  def Nodes(self):
    return self.__nodes

  @property
  def RFIDTags(self):
    return self.__rfidtags

  def ChangeUpdateInterval(self, interval):
    self.__sheets_update_interval_queue.put(interval)

  def AddLogs(self, log_object, write_mode = 'a'):
    '''
    Appends to the log file a new instance.

    Args:
      l: Log or list<Log>, the log object or list of log objects to be appended.
      write_mode: string, tells function whether it should append or rewrite all logs. Options:\n
        a: Append mode, adds log values to the end of the file.
        w: Write mode, truncates log values in file and writes logs.
    '''

    # Converts log(s) into line(s) string 
    def str_builder():
      txt = ""
      if isinstance(log_object, Log):
        txt = '\n' + str(log_object)
      elif isinstance(log_object, list):
        for log in log_object:
          if isinstance(log, Log):
            print('add')
            txt += '\n' + str(log)
      return txt

    # 'a' for append and 'w' for overwrite
    if write_mode == 'a':
      with open(self.__LOG_FILE, mode='a') as hf:
        hf.write(str_builder())
    elif write_mode == 'w':
      with open(self.__LOG_FILE, mode='w') as hf:
        hf.write(f"Timestamp,Status,EPC,Owner,Description,Location,Extra{str_builder()}")
        
    self.__print_out(f"saved logs to {self.__LOG_FILE}")

  def GetLogsFile(self):
    '''
    Retreives a list of logs from the logs file.

    Returns:
      list<Log>, all logs from the file
    '''

    # Pulls all lines from log file
    lf_lines = ""
    with open(self.__LOG_FILE, mode='r') as lf:
      lf_lines = lf.readlines()

    # Creates new log objects, skipping the first line since it's dedicated for the headers.
    logs = [Log(x) for x in lf_lines[1:]]
    return logs

  def LoadSettingsFile(self):
    """
    Opens settings from log file, creating a settings and log file if need be, and 
    moves the data into Handler internal variables.
    """

    # Attempts to open the file for updating and creates it if necessary.
    Path(self.__SETTINGS_FILE).touch()
    Path(self.__LOG_FILE).touch()
    rsf_data = None
    log_data = None

    # Attempts to read the binary data from the settings file
    with open(self.__SETTINGS_FILE, 'r+b') as sf:
      rsf_data = sf.read()

    # Attempts to read the TEXT data from the log file
    with open(self.__LOG_FILE, 'r') as lf:
      log_data = lf.read()

    # If settings file is empty, try to load from the Google Spreadsheet. Otherwise, use settings data
    if rsf_data == b"":
      self.ChangeSpreadsheet()
    else:
      # Deserializes file and pulls spreadsheet ID, rfid tags, and nodes.
      settings_obj = pickle.loads(rsf_data)
      self.__spreadsheetID = settings_obj['spreadsheet_id']
      self.__rfidtags = settings_obj['rfid_tags']
      self.__open_nodes_from_settings(settings_obj['nodes'])
      self.__print_out(f'loaded settings from {self.__SETTINGS_FILE}')

    if log_data == "":
      self.AddLogs(None, write_mode='w')

  def SaveSettingsFile(self):
    node_properties = [{'id' : node.ID, 'location' : node.Location} for node in self.Nodes]
    
    # Serializes settings and saves it to the settings file.
    pickle.dump({
      'spreadsheet_id' : self.__spreadsheetID,
      'rfid_tags' : self.__rfidtags,
      'nodes' : node_properties
    }, open(self.__SETTINGS_FILE, mode='wb'))      

    self.__print_out(f'saved settings to {self.__SETTINGS_FILE}')

  def LoadSheets(self):
    """
    Pulls data from the spreadsheet and loads them into Handler internal variables.
    """

    while True:
      try:
        # Get status from spreadsheet
        rfid_tag_values = self.__google_service.spreadsheets().values().get(spreadsheetId=self.__spreadsheetID, range=self.__RFIDTAGS_RANGE).execute().get('values', [])
        self.__rfidtags = [RFIDTag(*val) for val in rfid_tag_values]

        # Get logs from spreadsheet
        log_values = self.__google_service.spreadsheets().values().get(spreadsheetId=self.__spreadsheetID, range=self.__LOGS_RANGE).execute().get('values', [])
        self.__log_buffer = [Log(*val) for val in log_values]

        # Creates nodes from spreadsheet
        node_values = self.__google_service.spreadsheets().values().get(spreadsheetId=self.__spreadsheetID, range=self.__NODES_RANGE).execute().get('values', [])
        nodes_settings = [{ "id" : str(val[0]), "location" : str(val[1]) } for val in node_values]
        self.__open_nodes_from_settings(nodes_settings)

        break
      except ConnectionResetError: # In case the Google service object got disconnected
        self.__print_out('reconnecting to Google API...')
        self.__google_login()
    
    self.__print_out(f"loaded data from spreadsheet: '{self.__spreadsheetID}'")

  def UpdateSheets(self, log_mode = 'x'):
    '''
    Updates the spreadsheet with current nodes, rfid_tags, and logs

    Args:
      log_mode: string, represents whether the sheet should append the logs or rewrite them. Options:\n
        a: Append mode, adds all new logs.
        w: Write mode, truncates sheets log values and all inside of logs file.
        x: Skip mode, updates the node and RFID sheets and not the log sheet.
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

    # Compresses node, rfid tag, and log lists into rows for Google Sheets API
    node_vals = [[n.ID, n.Location, n.Status.value] for n in self.__nodes]
    rfid_tag_vals = [[r.EPC, str(r.Status), r.Owner, r.Description, r.LastLocation, r.Extra] for r in self.__rfidtags]
    log_vals = []

    if log_mode == 'a':
      log_vals = [[l.Timestamp.strftime(self.__DATETIME_FORMAT), l.EPC, str(l.Status), l.Owner, l.Description, l.Location, l.Extra] for l in self.__log_buffer]
    elif log_mode == 'w':
      log_vals = [[l.Timestamp.strftime(self.__DATETIME_FORMAT), l.EPC, str(l.Status), l.Owner, l.Description, l.Location, l.Extra] for l in self.GetLogsFile()]
    
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
        self.__google_service.spreadsheets().values().update(spreadsheetId=self.__spreadsheetID, range=self.__NODES_RANGE, body=node_resource, valueInputOption="RAW").execute()
        self.__google_service.spreadsheets().values().update(spreadsheetId=self.__spreadsheetID, range=self.__RFIDTAGS_RANGE, body=rfid_tags_resource, valueInputOption="RAW").execute()
        
        if (log_mode == 'a'):
          self.__google_service.spreadsheets().values().append(spreadsheetId=self.__spreadsheetID, range=self.__LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()
        elif (log_mode == 'w'):
          self.__google_service.spreadsheets().values().update(spreadsheetId=self.__spreadsheetID, range=self.__LOGS_RANGE, body=logs_resource, valueInputOption="RAW").execute()
        
        if log_mode != 'x': self.__log_buffer.clear() # Prevent duplicates being added to the spreadsheet
        break
      except ConnectionResetError:
        self.__print_out('reconnecting to Google API')
        self.__google_login()

    self.__print_out(f'saved data to {self.__spreadsheetID} spreadsheet')

  def SendCommandToNodes(self, command, *args):
    """Sends command to several or single nodes

    Args:
      command: Command, type of message to send
      *args: tuple, IDs of node(s) to send message
    """

    for node in args:
      node.SendMessage(command)
      self.__print_out(f"sending {command} to {node.ID}")

  def ChangeSpreadsheet(self):
    """
    Prompts user for a new spreadsheet ID, verifies the ID, and loads it into 
    Handler internal variables.

    Returns:
      bool, whether or not the load was successful
    """

    s_id = self.__command_reader.GetInput('Enter spreadsheet ID')

    if re.match(r'^[a-zA-Z0-9-_]+$', s_id, flags=re.RegexFlag.MULTILINE): # Refer to Google Sheets API documentation for Regex formula
      self.__spreadsheetID = s_id
      self.LoadSpreadsheet()
      return True

    return False

  def LoadSpreadsheet(self):
    self.LoadSheets()
    self.SaveSettingsFile()
    self.AddLogs(self.__log_buffer, 'w')
    self.__log_buffer.clear()
    self.UpdateSheets()

  def SafeClose(self):
    self.__shutdown_nodes()
    self.__stop_automatic_sheet_update_service()
    self.SaveSettingsFile()
    self.UpdateSheets(log_mode='a')

  def __google_login(self):
    """
    Opens a connection to Google Sheets API using the service account.
    """

    creds = service_account.Credentials.from_service_account_file(self.__SERVICE_ACC_FILE, scopes=self.__SCOPES) # Generate credentials object from service account file
    self.__google_service = build('sheets', 'v4', credentials=creds) # Create service object

  def __open_nodes_from_settings(self, node_settings):
    """
    Uses an object to create and automatically start nodes.

    Args:
      node_settings: list<object>, each object should be a dict with the fields\n
        'id' : [ID of the Node]
        'location' : [location of the node]
    """
    self.__quick_shutdown_nodes()
    self.__nodes = [Node(node['id'], node['location'], self.__receive_node_log, self.__receive_node_read_once_tag,
                    self.__receive_node_reader_reading, self.__receive_node_sensor_reading, self.__receive_node_error) for node in node_settings]

  def __shutdown_nodes(self):
    self.__print_out('shutting down nodes')
    for node in self.__nodes:
      node.Shutdown()

  def __quick_shutdown_nodes(self):
    for node in self.__nodes:
      node.QuickShutdown()

  def __receive_node_log(self, log, location):
    """Converts log from node into a log object, appends it to the current log list, and updates the RFID tag list.
    
    Args:
      log: object {
        'TIMESTAMP' : datetime, 
        'ID' : str,
        'BODY' : {
          "EPC" : str,
          "Status" : TagStatus,
          "RSSI" : int
        }
       }
    """

    # Attempts to find the index of the scanned tag and breaks out of the function if it's -1
    try:
      index = self.__rfidtags.index(next((tag for tag in self.__rfidtags if tag.EPC == log['BODY']['EPC']), None))
    except ValueError:
      return

    # Updates the the status and location of the tag to the status and 
    self.__rfidtags[index].Status = RFIDTag.Status(log['BODY']['Status'].value)
    self.__rfidtags[index].LastLocation = location

    # Create a new log object from the rfid tag
    new_log = Log(log['TIMESTAMP'], self.__rfidtags[index], location)

    self.__log_buffer.append(new_log)
    self.AddLogs(new_log)
    self.SaveSettingsFile()

  def __receive_node_read_once_tag(self, message, location):
    """Attempts to add new RFIDTag to the database.
    
    Args:
      message: object, {
        'TIMESTAMP' : datetime, 
        'ID' : str,
        'BODY' : {
          "EPC" : str,
          "Status" : TagStatus,
          "RSSI" : int
        }
       }
    """

    # Checks to see if the tag already exists and returns if it does
    if message['BODY']['EPC'] in [x.EPC for x in self.__rfidtags]:
      self.__print_out(f"Read an existing tag {message['BODY']['EPC']}")
      return

    # Prompts user if they would like to create a new RFID tag.
    yes_no_prompt = self.__command_reader.GetInput(f"Would you like to add a new RFIDTag with EPC '{message['BODY']['EPC']}'? (y/n)")

    # Returns if the user does not say yes.
    if yes_no_prompt.lower() != 'y' or yes_no_prompt.lower() != 'yes':
      return

    while True:
      # Prompt user for tag information 
      user_response = self.__command_reader.GetInput(f"Enter Owner, Description, and Extra")
      
      if len(user_response.split(sep=',')) == 3: # Input validation
        formatted_response = re.sub(r'(?<=,)\s', '', user_response) # Removes unecessary whitespace after ','s
        owner, description, extra = user_response.split(sep=',')
        self.__rfidtags.append(RFIDTag(message['BODY']['EPC'], message['BODY']['Status'], owner, description, location, extra))
        self.SaveSettingsFile()
        break
      else:
        yes_no_prompt = self.__command_reader.GetInput(f"Invalid tag info. Retry? (y/n)")
        if yes_no_prompt.lower() != 'y' or yes_no_prompt.lower() != 'yes': break

  def __receive_node_reader_reading(self, message):
    """Prints tag reading from the node.
    
    Args:
      message: object, {
        'TIMESTAMP' : datetime, 
        'ID' : str,
        'BODY' : {
          'EPC' : str,
          'Status' : TagStatus,
          'RSSI' : int
        }
       }
    """
    self.__print_out(f"{message['ID']}\t{message['BODY']['EPC']}")

  def __receive_node_sensor_reading(self, sensor_reading):
    """Prints sensor readings from the node.

    Args:
      message: object, {
        'TIMESTAMP' : datetime, 
        'ID' : str,
        'BODY' : {
          'Timestamp' : str,
          'SensorType' : SensorType,
          'Reading' : int
        }
       }
    """
    self.__print_out(f"{message['ID']}\t{str(message['BODY']['SensorType'])}\t{message['BODY']['Reading']}")

  def __receive_node_error(self, error):
    """Prints sensor readings from the node.

    Args:
      message: object, {
        'TIMESTAMP' : datetime, 
        'ID' : str,
        'BODY' : {
          'TRIGGER_COMMAND' : Command,
          'ERROR_MESSAGE' : Exception
        }
       }
    """
    self.__print_out(f"{message['ID']} reported {str(message['BODY']['ERROR_MESSAGE'])} after sending {message['BODY']['TRIGGER_COMMAND'].value}")

  def __receive_node_status(self, status):
    self.__print_out(f"node is now {status.value}")

  def __print_out(self, message):
    print(f"{datetime.datetime.now().strftime(self.__DATETIME_FORMAT)}\t{message}")

  def __start_automatic_sheet_update_service(self):
    '''
    Updates the GSheets file periodically

    Args:
      update: int, amount of sheet updates per day.
    '''

    time_count = 0
    timeslice = 0
    self.__print_out('running automatic sheet updates')

    while self.__automatic_sheets_update_running:
      try:
        # Checks to see if there's a new interval
        interval = self.__sheets_update_interval_queue.get_nowait()
        timeslice = 24 / interval * 3600
      except queue.Empty: pass

      # Updates spreadsheet
      if time_count == timeslice:
        self.UpdateSheets(log_mode='a')
        time_count = 0

      time_count += 1
      time.sleep(1)

  def __stop_automatic_sheet_update_service(self):
    """
    Disables the automatic sheet updates
    """
    self.__automatic_sheets_update_running = False

handler = Handler()