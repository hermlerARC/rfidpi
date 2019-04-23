import threading, queue, re, enum
from node_enums import Command
from tabulate import tabulate

class CommandReader:
  class Command(enum.Enum):
    UNRECOGNIZED = 0
    EXIT = 1
    SPREADSHEET = 2
    NODES = 3
    EDIT = 4
    DISPLAY = 5
    HELP = 6

    CHANGE_SHEET = 7
    UPDATE_SHEET = 8
    LOAD_SHEET = 9
    SET_INTERVAL = 10

    APPEND = 11
    OVERWRITE = 12
    SKIP = 13

  def __init__(self, handler):
    self.__handler = handler

    self.__running = False
    self.__using_commands = False
    self.__using_commands_queue = queue.Queue()

  def Start(self):
    if self.__running:
      raise RuntimeError('Attempted to start CommandReader while it was already running')
    
    self.__running = True
    cr_thread = threading.Thread(target=self.__run)
    cr_thread.start()

  def Stop(self):
    self.__handler.SafeClose()
    self.__running = False

  def GetInput(self, message=""):
    self.__using_commands = True

    if message != "":
      print(message, end=': ')
    text_response = input()
    self.__using_commands = False

    return text_response
  
  def __run(self):
    while self.__running:
      try:
        text = input() # Gets input from standard input
      except KeyboardInterrupt:
        self.Stop()
        
      if text == "" or self.__using_commands:
        continue

      commands = iter(text.split(sep=' '))
      first_command = self.__get_first_command(next(commands, ""))

      if first_command == CommandReader.Command.UNRECOGNIZED:
        self.__print_error(f"Invalid first command in: '{text}'")
      elif first_command == CommandReader.Command.EXIT:
        self.Stop()
      elif first_command == CommandReader.Command.SPREADSHEET:
        spreadsheet_command = self.__get_spreadsheet_command(next(commands, ""))

        if spreadsheet_command == Command.CHANGE_SHEET:
          if not self.__handler.ChangeSpreadsheet():
            self.__print_error(f"Invalid spreadsheet ID: '{new_spreadsheetID}'")
        elif spreadsheet_command == Command.UPDATE_SHEET:
          update_type = next(commands, default="-a")
          
          if update_type == '-a' or update_type == '-w' or update_type == '-x':
            self.__handler.UpdateSheets(log_mode=update_type[1:])
          else:
            self.__print_error(f"Invalid update type: {update_type}")
        elif spreadsheet_command == Command.LOAD_SHEET:
          if input('You might have unsaved data. Are you sure you want to overwrite? (y/n)').upper() == 'Y':
            self.__handler.LoadSpreadsheet()
        elif spreadsheet_command == Command.SET_INTERVAL:
          interval_speed = next(commands, default=0)
          if interval_speed.isdigit() and int(interval_speed) > 0:
            self.__handler.ChangeUpdateInterval(interval_speed)
          else:
            self.__print_error('Interval speed must be an integer greater than 0')
        else:
          self.__print_error('Invalid spreadsheet command')
      elif first_command == CommandReader.Command.NODES:
        node_command = next(commands, None)
        node_argument = next(commands, '-a')
        selected_nodes = next(commands, "").split(sep=',')
        
        if node_command in [command.value for command in Command]:
          command = Command(node_command)
          if node_argument == '-a':
            self.__handler.SendCommandToNodes(command, *(self.__handler.Nodes))
          if node_argument == '-s':
            nodes = list(filter(lambda x: x.ID in selected_nodes, self.__handler.Nodes))
            if len(nodes) == "":
              self.__print_error(f"Could not find specificed node(s): {', '.join(nodes)}")
            else:
              self.__handler.SendCommandToNodes(command, *nodes)
        else:
          self.__print_error("Unrecognized command. Unable to send to node(s)")  
      elif first_command == CommandReader.Command.EDIT:
        raise NotImplementedError
      elif first_command == CommandReader.Command.DISPLAY:
        display_command = next(commands, 'a')

        if display_command == 'a':
          self.__print_spreadsheet()
          self.__print_nodes()
          self.__print_tags()
          self.__print_logs(int(next(commands, 5)))
        elif display_command == 's':
          self.__print_spreadsheet()
        elif display_command == 'r':
          self.__print_tags()
        elif display_command == 'n':
          self.__print_nodes()
        elif display_command == 'l':
          self.__print_logs(int(next(commands, 5)))
      elif first_command == CommandReader.Command.HELP:
        self.ShowHelp()

  def __get_first_command(self, name):
    if name == 'x' or name == 'exit':
      return CommandReader.Command.EXIT
    elif name == 's' or name == 'spreadsheet':
      return CommandReader.Command.SPREADSHEET
    elif name == 'n' or name == 'nodes':
      return CommandReader.Command.NODES
    elif name == 'e' or name == 'edit':
      return CommandReader.Command.EDIT
    elif name == 'd' or name == 'display':
      return CommandReader.Command.DISPLAY
    elif name == 'h' or name == 'help':
      return CommandReader.Command.HELP
    else:
      return CommandReader.Command.UNRECOGNIZED

  def __get_spreadsheet_command(self, name):
    if name == 'c':
      return CommandReader.Command.CHANGE_SHEET
    elif name == 'u':
      return CommandReader.Command.UPDATE_SHEET
    elif name == 'l':
      return CommandReader.Command.LOAD_SHEET
    elif name == 'i':
      return CommandReader.Command.SET_INTERVAL
    else:
      return CommandReader.Command.UNRECOGNIZED

  def __get_update_type(self, name):
    if name == '-a':
      return CommandReader.Command.APPEND
    elif name == '-w':
      return CommandReader.Command.OVERWRITE
    elif name == '-x':
      return CommandReader.Command.SKIP
    else:
      return CommandReader.Command.UNRECOGNIZED

  def __print_error(self, msg):
    print(f"{msg}. Use 'h' for help.")

  def __print_spreadsheet(self):
    print('\r\n')
    print(tabulate([[self.__handler.SpreadSheetID]], headers=['Spreadsheet ID'], tablefmt="rst"))

  def __print_nodes(self):
    print('\r\nNodes:\r\n')
    nodes = list(map(lambda v: [v.ID, v.Location, v.Status], self.__handler.Nodes))
    print(tabulate(nodes, headers=['ID', 'Location', 'Status'], tablefmt="rst"))

  def __print_tags(self):
    print('\r\nTags:\r\n')
    tags = list(map(lambda v: str(v).split(sep=','), self.__handler.RFIDTags))
    print(tabulate(tags, headers=['EPC', 'Status', 'Owner', 'Description', 'Last Location', 'Extra'], tablefmt="rst"))

  def __print_logs(self, rows):
    print('\r\nLogs:\r\n')
    logs = list(map(lambda v: str(v).split(sep=','), self.__handler.GetLogsFile()[-rows:]))
    print(tabulate(logs, headers=['Timestamp', 'EPC', 'Status', 'Owner', 'Description', 'Location', 'Extra'], tablefmt="rst"))

#region Help
  def ShowHelp(self):
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
readers|r [message] -option [id1,id2,...]
  Description: Accesses readers
  Message:
    start_logging - Tells node to read like normal.
    read_once - Tells node to read one tag.
    stop_logging - Tells node to stop reading.
    begin_sensor_test - Tells node to continuously output sonic sensor reads.
    begin_reader_test - Tells node to continously output RFID tag reads.
    stop_sensor_test - Tells node to stop the sensor test.
    stop_reader_test - Tells node to stop the reader test.
    check_status - Requests the current state of the node.
    ping - Wildcard. Doesn't actually do anything except check for a response from the node.
  Options:
    a - Accesses all nodes. Must specify a message.
    i - Acceses a specific nodes. 
  ID: ID of a reader. Refer to readers!a1:a for reader IDs on spreadsheet.
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
#endregion