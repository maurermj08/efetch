#!/bin/bash

#Check that the script is run as root
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

#Install Repo Dependencies
echo 'Installing Efetch dependencies...'
sudo add-apt-repository -y ppa:gift/stable
sudo add-apt-repository -y ppa:sift/stable
sudo apt-get update
sudo apt-get -y install python-plaso python-dev python-setuptools unoconv libpff libpff-python zlib1g-dev libjpeg-dev libtiff5-dev
python ${PWD}/setup.py install
echo 'Done!'
