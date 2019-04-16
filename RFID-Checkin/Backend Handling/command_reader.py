import threading, queue, re, enum
from tabulate import tabulate

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

class CommandReader:
  def __init__(self, handler):
    self.__handler = handler

    self.__running = False
    self.__using_commands = False
    self.__using_commands_queue = queue.Queue()

  def Start(self):
    if self.__running:
      print('Attempted to start CommandReader while it was already running')
      raise RuntimeError
    
    self.__running = True
    cr_thread = threading.Thread(target=__run)
    cr_thread.start()

  def Stop(self):
    self.__running = False

  def GetInput(self):
    self.__using_commands = True

    text_response = self.__using_commands_queue.get()
    self.__using_commands = False

    return text_response
  
  def __run(self):
    while self.__running:
      text = input() # Gets input from standard input

      if text == "":
        continue

      if self.__using_commands == True:
        self.__using_commands_lock.put(text)
        continue

      commands = iter(text.split(sep=' '))
    
      first_command = self.__get_first_command(next(commands, default=""))

      if first_command == Command.UNRECOGNIZED:
        self.__print_error(f"Invalid first command in: '{text}'")
      elif first_command == Command.EXIT:
        self.__running = False
      elif first_command == Command.SPREADSHEET:
        spreadsheet_command = self.__get_spreadsheet_command(next(commands, default=""))

        if spreadsheet_command == Command.CHANGE_SHEET:
          new_spreadsheetID = next(commands, default="")
          if re.match("^[a-zA-Z0-9-_]+$", new_spreadsheetID, flags=re.MULTILINE):
            self.__handler.SetSpreadsheetID(new_spreadsheetID)
            print("It's recommended to run 's l' to load the new spreadsheet values.")
          else:
            self.__print_error(f"Invalid spreadsheet ID: '{new_spreadsheetID}'")
        elif spreadsheet_command == Command.UPDATE_SHEET:
          update_type = next(commands, default="-a")

          if update_type == '-a' or update_type == '-w' or update_type == '-x':
            self.__handler.SaveSheet(update_type)
          else:
            self.__print_error(f"Invalid update type: {update_type}")
        elif spreadsheet_command == Command.LOAD_SHEET:
          if input('You might have unsaved data. Are you sure you want to overwrite? (y/n)').capitalize() == 'Y':
            self.__handler.LoadSheets()
            self.__handler.SaveSetupFile()
            self.__handler.UpdateLogFile('w')
            self.__handler.ClearLogs()
        elif spreadsheet_command == Command.SET_INTERVAL:
          interval_speed = next(commands, default=0)
          if interval_speed.isdigit() and int(interval_speed) > 0:
            self.__handler.SetUpdatesInterval(interval_speed)
          else:
            self.__print_error('Interval speed must be an integer greater than 0')
        else:
          self.__print_error('Invalid spreadsheet command')
      
      elif first_command == Command.NODES:
        node_command = self.__get_node_command(next(commands, default=""))
        node_argument = next(commands, default='-a')
        selected_nodes = next(commands, default="").split(sep=',')

        if node_argument == '-a':
          self.__handler.SendNodeMessage(node_command)
        if node_argument == '-s':
          if selected_nodes == "":
            self.__print_error('Must specify which nodes to send a message')
          else:
            self.__handler.SendNodeMessage(node_command, selected_nodes)
    
      elif first_command == Command.EDIT:
        pass
      elif first_command == Command.DISPLAY:
        pass
      elif first_command == Command.HELP:
        self.ShowHelp()
      
      elif command.group(1) == 'r' or command.group(1) == 'readers':

        if command.group(4) == 'a':
          if command.group(5) == None:
            show_help(f"Must specify a message to send to node(s): {', '.join(list(map(lambda n: n.ID, nodes)))}")
          else:
            if command.group(6) and re.match(r'(?:\d+(?:\.(?=\d+))?|\.\d+)', command.group(6)):
              send_message_wrapper(0, command.group(5), False, timeout=float(command.group(6)))
            else:
              send_message_wrapper(0, command.group(5), False)
        elif command.group(4) == 'i':
          if not command.group(5) in list(map(lambda n: n.ID, nodes)):
            show_help(f'Could not find reader: {command.group(5)}')
          else:
            if command.group(6) == None:
              show_help(f"Must specify message to send to: {command.group(5)}")
            else:
              packet = command.group(6).split(sep=' ')
              ind = nodes.index(next(n for n in nodes if n.ID == command.group(5)))
              if len(packet) == 2 and re.match(r'(?:\d+(?:\.(?=\d+))?|\.\d+)', packet[1]):
                send_message_wrapper(ind, packet[0], True, timeout=float(packet[1]))
              else:
                send_message_wrapper(ind, packet[0], True)             
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

  def __get_first_command(self, name):
    if name == 'x' or name == 'exit':
      return Command.EXIT
    elif name == 's' or name == 'spreadsheet':
      return Command.SPREADSHEET
    elif name == 'n' or name == 'nodes':
      return Command.NODES
    elif name == 'e' or name == 'edit':
      return Command.EDIT
    elif name == 'd' or name == 'display':
      return Command.DISPLAY
    elif name == 'h' or name == 'help':
      return Command.HELP
    else:
      return Command.UNRECOGNIZED

  def __get_spreadsheet_command(self, name):
    if name == 'c':
      return Command.CHANGE_SHEET
    elif name == 'u':
      return Command.UPDATE_SHEET
    elif name == 'l':
      return Command.LOAD_SHEET
    elif name == 'i':
      return Command.SET_INTERVAL
    else:
      return Command.UNRECOGNIZED

  def __get_update_type(self, name):
    if name == '-a':
      return Command.APPEND
    elif name == '-w':
      return Command.OVERWRITE
    elif name == '-x':
      return Command.SKIP
    else:
      return Command.UNRECOGNIZED


  def __print_error(self, msg):
    print(f"{err_msg}. Use 'h' for help.")

  def __print_spreadsheet(self):
    print('\r\n')
    print(tabulate([[self.__handler.GetSpreadsheetID()]], headers=['Spreadsheet ID'], tablefmt="rst"))

  def __print_nodes(self):
    print('\r\nNodes:\r\n')
    nodes = list(map(lambda v: str(v).split(sep=','), self.__handler.GetNodes()))
    print(tabulate(nodes, headers=['ID', 'Location', 'Status'], tablefmt="rst"))

  def __print_tags(self):
    print('\r\nTags:\r\n')
    tags = list(map(lambda v: str(v).split(sep=','), self.__handler.GetTags()))
    print(tabulate(tags, headers=['EPC', 'Status', 'Owner', 'Description', 'Location', 'Extra'], tablefmt="rst"))

  def __print_logs(self, rows):
    print('\r\nLogs:\r\n')
    logs = list(map(lambda v: str(v).split(sep=','), self.__handler.GetLogs(rows)))
    print(tabulate(logs, headers=['Timestamp', 'Status', 'EPC', 'Owner', 'Description', 'Location', 'Extra'], tablefmt="rst"))


#region Help
  def ShowHelp():
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
readers|r -option [ID|message] [message] [timeout=5]
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
    Timeout: 
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

"""
 '''
  Starts seperate thread that executes commands read from the standard input.
  '''
  
  def save_sheet_wrapper(response, topic, msg):
    if response == MQTTResponse.SUCCESSFUL:
      save_sheet(log_mode='x')

  def send_message_wrapper(node_ind, msg, single, timeout=float(5)):
    read_or_stop = msg == 'read' or msg == 'stop'
    if (node_ind < len(nodes)):
      if single:
        if read_or_stop:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=timeout, callback=save_sheet_wrapper)
        else:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=timeout)
      else:
        if read_or_stop:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=timeout, callback=save_sheet_wrapper, callback2=send_message_wrapper, args=(node_ind + 1, msg, single, timeout))
        else:
          send_message(f"reader/{nodes[node_ind].ID}/status", msg, timeout=timeout, callback2=send_message_wrapper, args=(node_ind + 1, msg, single, timeout))

  def read_command():
    while cr_running:
      
  
    save_close()
  # Start the thread
  rc_thread = threading.Thread(target=read_command)
  rc_thread.daemon = True
  rc_thread.start()
"""