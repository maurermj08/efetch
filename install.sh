#!/bin/bash

#Check that the script is run as root
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

#Install Repo Dependencies
echo 'Installing Efetch dependencies...'
sudo add-apt-repository ppa:gift/stable
sudo apt-get update
sudo apt-get -y install python-plaso python-dev python-pip default-jre elasticsearch unoconv
sudo update-rc.d elasticsearch defaults
sudo service elasticsearch start

#Install Efetch Dependencies
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
sudo pip install -r $DIR/requirements.txt


#PLASO FUNCTIONALITY:
echo 'Adding Efetch to Plaso and modifying file_stat...'
sudo cp $DIR/misc/plaso/events/file_system_events.py /usr/lib/python2.7/dist-packages/plaso/events/.
sudo cp $DIR/misc/plaso/parsers/filestat.py /usr/lib/python2.7/dist-packages/plaso/parsers/.
sudo cp $DIR/misc/plaso/output/efetch.py /usr/lib/python2.7/dist-packages/plaso/output/.
sudo cp $DIR/misc/plaso/cli/helpers/efetch_output.py /usr/lib/python2.7/dist-packages/plaso/cli/helpers/.
echo "from plaso.output import efetch" | sudo tee --append /usr/lib/python2.7/dist-packages/plaso/output/__init__.py
echo "from plaso.cli.helpers import efetch_output" | sudo tee --append /usr/lib/python2.7/dist-packages/plaso/cli/helpers/__init__.py

#Installing external dependencies
wget https://github.com/williballenthin/python-registry/archive/master.zip
unzip master.zip
sudo python-registry-*/setup.py install

echo 'Done!'
