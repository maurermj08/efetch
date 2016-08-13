#!/bin/bash

# Copyright 2016 Michael J Maurer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
chmod g-wx,o-wx ~/.python-eggs
echo 'Done!'
