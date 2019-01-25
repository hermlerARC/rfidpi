import datetime
import mercury
from googleapiclient.discovery import build
from google.oauth2 import service_account

IDS = []
SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Read and write permissions for program
SERVICE_ACCOUNT_FILE = 'service.json'
SPREADSHEET_IDS = '1BG00G_G9gz2YZyTSguNjZIt1ylyPHvZ16A5l7cF0RM8'
SPREADSHEET_LOG = '1Wba4aHYVMdg2diixStky0tDLOEgd5M5Z9oG-JL6K2_Q' # Spreadsheet ID for list of ids, names, and clubs
RANGE_IDS = 'IDS!a2:c'
RANGE_LOG = 'log!a2:d'

r = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
r.set_region("NA")

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES) # Generate credentials object from service account file
service = build('sheets', 'v4', credentials=creds) # Create service object
idVals = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=RANGE_IDS).execute().get('values', []) # Get values from IDs spreadsheet

def readTags(e):
    for tag in e:
        epc = str(tag.epc, 'utf-8')
        if (any(j[0][0] == epc for j in IDS)):
            row = []
            update = {}
            id = next(j for j in IDS if j[0][0] == epc)
            index = IDS.index(next(j for j in IDS if j[0][0] == epc))
            updateRange = "IDS!c%s" % (index+2)
            now = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
            if id[2][0] == "in":
                row = [[now], [id[0][0]], [id[1][0]], ["out"]]
                update = {"majorDimension": "COLUMNS", "values": [["out"]]}
                IDS[index][2] = ["out"]
            elif id[2][0] == "out":
                row = [[now], [id[0][0]], [id[1][0]], ["in"]]
                update = {"majorDimension": "COLUMNS", "values": [["in"]]}
                IDS[index][2] = ["in"]
                
            resource = {
                "majorDimension": "COLUMNS",
                "values": row # Creates row object formatted as: Time, Name, ID, Club
            }
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_LOG,
                range=RANGE_LOG,
                body=resource,
                valueInputOption="RAW"
            ).execute() # Append new line to LOG sheet
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_IDS,
                range=updateRange,
                body=update,
                valueInputOption="RAW").execute()
            

for x in idVals:
    IDS.append([[x[0]], [x[1]], [x[2]]])
    
try:
    print("Start scanning\n")
    while True:
        readTags(r.read(timeout=1000))
except KeyboardInterrupt:
    pass
    
