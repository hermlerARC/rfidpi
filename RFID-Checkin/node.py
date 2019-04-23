import enum, threading, datetime, pickle
from node_enums import *
from paho.mqtt import client

class Node:
  __DICT_VALUES = ['ID', 'Location', 'ErrorCallback', 'LoggingCallback', 'ReadOnceCallback', 'SensorTestingCallback', 'ReaderTestingCallback']
  __CONNECTIVITY_TIMEOUT = 2
  __MAX_CONNECTION_ATTEMPTS = 5

  def __init__(self, *args, **kwargs):
    """Opens a connection to a node. Allows for sending and receiving messages

    kwargs:
      ID: str, unique ID of node
      Location: str, location of node
      LoggingCallback: function, called when a tag needs to be logged
      ReadOnceCallback: function, called after a node has replied to a single tag request
      SensorTestingCallback: function, called when receiving a sensor reading value
      ReaderTestingCallback: function, called when receiving a tag value with no direction
      ErrorCallback: function, called whenever the node reports an error
    """
    if all(val in kwargs for val in Node.__DICT_VALUES):
      self.__id = kwargs['ID']
      self.__location = kwargs['Location']
      self.__logging_callback = kwargs['LoggingCallback']
      self.__read_once_callback = kwargs['ReadOnceCallback']
      self.__sensor_callback = kwargs['SensorTestingCallback']
      self.__reader_callback = kwargs['ReaderTestingCallback']
      self.__error_callback = kwargs['ErrorCallback']
    elif len(args) == 7:
      self.__init__(ID=args[0], Location=args[1], LoggingCallback=args[2], ReadOnceCallback=args[3], SensorTestingCallback=args[4], ReaderTestingCallback=args[5], ErrorCallback=args[6])
      return
    else:
      raise ValueError(f"Must specify values for {', '.join(Node.__DICT_VALUES)}")
      
    self.__status = Status.OFFLINE
    self.__closing = False
    
    self.__node_replies = []
    self.__node_replies_lock = threading.Lock()

    self.__client = client.Client(transport='websockets') # Connect with websockets
    self.__client.on_connect = self.__on_connect
    self.__client.on_message = self.__on_message
    self.__client.connect('broker.hivemq.com', port=8000)

    threading.Thread(target=self.__client.loop_forever).start()

  def __str__(self):
    return f"{self.__id},{self.__location},{str(self.__connected)}"

#region Public
  def SendMessage(self, message):
    if isinstance(message, Command):
      threading.Thread(target=self.__send_message, args=(message,)).start()

  def CheckStatus(self):
    self.__send_message(Command.CHECK_STATUS)
    return self.__status

  def QuickShutdown(self):
    self.__closing = True
    self.__client.disconnect()

  def Shutdown(self):
    self.SendMessage(Command.STOP_LOGGING)
    self.SendMessage(Command.STOP_READER_TEST)
    self.SendMessage(Command.STOP_SENSOR_TEST)

    self.__closing = True
    self.__client.disconnect()

  def Reset(self):
    self.Shutdown()
    self.__init__(self.__id, self.__locaiton)

  @property
  def ID(self):
    return self.__id  

  @property
  def Location(self):
    return self.__location

  @property
  def Status(self):
    return self.__status

  @property
  def NodeConnected(self):
    return self.__send_message(Command.PING, timeout=Node.__CONNECTIVITY_TIMEOUT)
#endregion

  def __send_message(self, message, callback=None, timeout = 15):
    if not isinstance(timeout, int) or timeout < 0:
      raise ValueError("Invalid timeout argument. Timeout must be an integer greater than 0.")
    if not isinstance(message, Command):
      raise ValueError("Invalid message argument. Must be of type Command")
    
    self.__client.publish(f'reader/{self.__id}/{Topic.COMMANDS}', pickle.dumps(message), qos=1)

    start_time = datetime.datetime.now()
    expected_response = repr(message)
    received_response = False
    
    while not (received_response or self.__closing) and (datetime.datetime.now() - start_time).total_seconds() <= timeout:
      self.__node_replies_lock.acquire()
      if expected_response in self.__node_replies:
        self.__node_replies.remove(expected_response)
        received_response = True
      self.__node_replies_lock.release()
    
    if received_response:
      print(f"got response after {(datetime.datetime.now() - start_time).total_seconds() * 1000} ms")
    return received_response

  def __on_connect(self, client, data, flags, rc):
    client.subscribe(f'reader/{self.__id}/{Topic.NODE_STATUS}', 1) 
    client.subscribe(f'reader/{self.__id}/{Topic.NODE_RESPONSE}', 1) 
    client.subscribe(f'reader/{self.__id}/{Topic.TAG_READINGS}', 1) 
    client.subscribe(f'reader/{self.__id}/{Topic.SENSOR_READINGS}', 1)
    client.subscribe(f'reader/{self.__id}/{Topic.ERROR_CODES}', 1)

    self.CheckStatus()

  def __on_message(self, client, data, msg):
    message_obj = pickle.loads(msg.payload)
    topic = Topic(msg.topic.split(sep='/')[2])

    if topic == Topic.NODE_STATUS:
      self.__status = message_obj['BODY']
    elif topic == Topic.NODE_RESPONSE:
      self.__node_replies_lock.acquire()
      self.__node_replies.append(message_obj['BODY'])
      print(f"added item {message_obj['BODY']}")
      self.__node_replies_lock.release()
    elif topic == Topic.TAG_READINGS:
      if self.__status == Status.LOGGING:
        self.__logging_callback(message_obj, self.Location)
      elif self.__status == Status.REQUESTING_TAG:
        self.__read_once_callback(message_obj, self.Location)
        self.__read_once_callback = None
      elif self.__status == Status.RUNNING_READER_TEST:
        self.__reader_callback(message_obj)
    elif topic == Topic.SENSOR_READINGS:
      self.__sensor_callback(message_obj)
    elif topic == Topic.ERROR_CODES:
      self.__error_callback(message_obj)
