# efetch
Evidence Fetcher (efetch) is a web-based file explorer, viewer, and analyzer. Efetch supports viewing hundreds of file types including office, registry, PST, image, and SQLite files. Efetch supports navigating RAW, E01, ZIP, GZ, TAR, VMDK, VHD, QCOW, and BZ2 files thanks to dfVFS.

# Install

Efetch depends on the following files:
* python
* plaso
* setuptools (>=28.5.0)
* pip
* libpff
* zlib
* libjpeg
* libtff
    
On Ubuntu 14.04 these packages can be installed using the following command:

```bash
sudo add-apt-repository -y ppa:gift/stable
sudo add-apt-repository -y ppa:sift/stable
sudo apt-get update
sudo apt-get install python-plaso python-dev python-setuptools unoconv libpff libpff-python zlib1g-dev libjpeg-dev libtiff5-dev python-pip
sudo pip install setuptools -U
```

Once these dependencies are met, efetch can be installed using the python setup tools.

```bash
python setup.py install
```

# Usage

After installation run the command **efetch** in the terminal and navigate to **localhost:8080** in a browser. From the home page, either browse your local file system directly using the **browse** option or enter a **pathspec**. Evidence can be navigated by simply clicking the file name or icon.

![alt tag](https://cloud.githubusercontent.com/assets/13810976/19585127/e1bb1e08-9717-11e6-8fcf-069be4b4957c.gif)

The **efetch** command supports the following arguments:
```
usage: efetch [-h] [-d] [-v] [-a ADDRESS] [-p PORT] [-e ELASTIC] [-c CACHE]
              [-m MAXFILESIZE] [-f PLUGINSFILE]

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           Displays debug messages
  -v, --version         Prints Efetch version
  -a ADDRESS, --address ADDRESS
                        IP address for the Efetch server
  -p PORT, --port PORT  Port for the Efetch server
  -e ELASTIC, --elastic ELASTIC
                        Elasticsearch URL, i.e. localhost:9200
  -c CACHE, --cache CACHE
                        Directory to store cached files
  -m MAXFILESIZE, --maxfilesize MAXFILESIZE
                        Max file size to cache in Megabytes, default 1GB
  -f PLUGINSFILE, --pluginsfile PLUGINSFILE
                        Path to the plugins config file

```

# Plugins

Efetch can be easily extended with simple plugins by editing the /etc/efetch_plugin.yml file. Efetch automatically detects any changes to the plugin file. Below is an example of a ClamAV efetch plugin:

```
  clamscan:
    name: Clam Scan
    command: "clamscan '{{ file_cache_path }}'"
```

Additionally, efetch supports more advanced python plugins. These plugins can be created using the scripts/create_plugin.py script. For more information see https://github.com/maurermj08/efetch/wiki/Create-Plugin.

# Note

Efetch is in Beta and really needs the community's support, so please post any bugs. As far as this project is concerned, there is no such thing as a bad bug report.

For more information about efetch please see: https://github.com/maurermj08/efetch/wiki
