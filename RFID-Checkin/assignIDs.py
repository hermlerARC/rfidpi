import mercury
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/spreadsheets'] # Read and write permissions for program
SERVICE_ACCOUNT_FILE = 'service.json'
SPREADSHEET_IDS = '1BG00G_G9gz2YZyTSguNjZIt1ylyPHvZ16A5l7cF0RM8' # Spreadsheet ID for list of ids, names, and clubs
RANGE_IDS = 'IDS!a2:c'

IDS = []

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

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES) # Generate credentials object from service account file
service = build('sheets', 'v4', credentials=creds) # Create service object
vals = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_IDS, range=RANGE_IDS).execute().get('values', []) # Get values from IDs spreadsheet
        
def main():
    for x in vals:
        IDS.append([[x[0]],[x[1]], [x[2]]])

    r = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=9600)
    r.set_region("NA")

    try:
        print("Begin assigning\n")
        while True:
            readTag(r.read())
    except KeyboardInterrupt:
        pass
    
if __name__ == '__main__':
    main()
    


