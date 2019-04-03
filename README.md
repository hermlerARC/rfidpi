# RFID-Checkin

Install dependencies for raspi:

git clone https://github.com/gotthardp/python-mercuryapi.git

cd python-mercuryapi

sudo apt-get install patch xsltproc gcc libreadline-dev python-dev python-setuptools

make PYTHON=python3

make install

pip install paho-mqtt

pip install --upgrade google-api-python-client oauth2client

