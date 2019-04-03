# RFID Logging Software 

## Parts Used:
* Raspberry Pi Model 3 [Buy](https://www.raspberrypi.org/products/raspberry-pi-3-model-b/)
* ThingMagic USB RFID Reader
* 2 x HCSR04 Sonic Readers

## Install Instructions:

1. Get a duplicate of the [spreadsheet template](https://docs.google.com/spreadsheets/d/1U1NcnHXWjDb0NeJ3oTpLPU2vhdeKHef8IizWEw00A-0/edit?usp=sharing).
2. Share the document with security-head@rfid-security-221905.iam.gserviceaccount.com. *(Optional)* You can create and share with your own service account by following these [instructions](https://developers.google.com/identity/protocols/OAuth2ServiceAccount). Just make sure to enable the Google Sheets API.
3. Install dependencies on the client. These libraries must be installed on Python 3.6+.
```
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip3 install paho-mqtt
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
