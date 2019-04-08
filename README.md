# RFID Logging Software 

This project was designed to aid the music department at American River College in preventing theft of instruments. It uses UHF RFID technology and sonic readers to determine direction of travel to track the instruments location. It then sends this data using MQTT to a client, combined with tag data from other devices, where it is then processed and stored locally on the client file system. The data is then uploaded to Google Sheets on an interval or when manually instructed.

## Parts Used:
* 1 x [Raspberry Pi Model 3](https://www.raspberrypi.org/products/raspberry-pi-3-model-b/) ($35)
* 1 x [ThingMagic USB RFID Reader](https://www.atlasrfidstore.com/thingmagic-usb-plus-rfid-reader/) ($400)
* 2 x [HCSR04 Sonic Readers](https://www.sparkfun.com/products/13959) ($5)

## Diagrams
### Wiring
![wiring diagram](https://github.com/hermlerARC/rfidpi/blob/master/Diagrams/Sensor%20Wiring.png?raw=true)
### Data Flow Diagram
![data flow diagram](https://github.com/hermlerARC/rfidpi/blob/master/Diagrams/Data%20Flow%20Diagram.jpg?raw=true)
### How RFID Works
![rfid diagram](https://howtomechatronics.com/wp-content/uploads/2017/05/RFID-Working-Principle.png)
## Install Instructions:
1. Get a duplicate of the [spreadsheet template](https://docs.google.com/spreadsheets/d/1IgreAi3hvmLa3X66jhwo6dZCcqReNV2zIlWpLoTB3LY).
2. Share the document with security-head@rfid-security-221905.iam.gserviceaccount.com. *(Optional)* You can create and share with your own service account by following these [instructions](https://developers.google.com/identity/protocols/OAuth2ServiceAccount). Just make sure to enable the Google Sheets API.
3. Install dependencies on the client. These libraries must be installed on Python 3.6+.
```
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip3 install paho-mqtt
pip3 install tabulate
```
4. Install dependencies on the Raspberry Pi:
This will soon be deprecated as a duplicable image is made for the Raspberry Pi. Must be installed on Python 3.5+.
```git clone https://github.com/gotthardp/python-mercuryapi.git
cd python-mercuryapi
sudo apt-get install patch xsltproc gcc libreadline-dev python-dev python-setuptools
make PYTHON=python3
make install
pip3 install paho-mqtt
```
5. Follow wiring and data flow diagrams to setup the physical devices.
6. Run `RFID-Checkin/Raspi code/read.py` on Raspberry Pi.
7. Run `RFID-Checkin/Backend Handling/handler.py` on a client computer.
9. Enter a Google Spreadsheets ID. 
8. Send handler.py the command: `r -a read`

## Notes
- Contributors: Dominique Stepek, Gavin Furlong,  Abdullah Shabir, Prof. Ryan Hermle
- More reading: [Google Sheets API](https://developers.google.com/sheets/api/), [MQTT](http://mqtt.org/), [Mercury API for Python](https://github.com/gotthardp/python-mercuryapi) 
- `RFID-Checkin/Backend Handling/handler.py` supports the ability to interface with the local storage, sheets, and nodes through commands. Just input `h` for help.
- This project was programmed to interface with the Mercury API which requires ThingMagic RFID readers. 
- RFID tags must respond to the UHF RFID band (860 to 960 MHz) to be read by the reader 
