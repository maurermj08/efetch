# efetch
Evidence Fetcher (efetch) is a web-based file explorer, viewer, and analyzer. Efetch supports viewing hundreds of file types including office, registry, PST, image, and SQLite files. Efetch supports navigating RAW, E01, ZIP, GZ, TAR, VMDK, VHD, QCOW, and BZ2 files thanks to dfVFS.

After installation run the command **efetch** in the terminal and navigate to **localhost:8080** in a browser. Use the **expand** plugin to navigate into evidence files.

![alt tag](https://cloud.githubusercontent.com/assets/13810976/19025778/825659c6-88eb-11e6-988c-b16d28b1eae5.gif)

Efetch can be easily extended with simple plugins by editing the /etc/efetch_plugin.yml file. Efetch automatically detects any changes to the plugin file. Below is an example of a ClamAV efetch plugin:

```
  clamscan:
    name: Clam Scan
    command: "clamscan '{{ file_cache_path }}'"
```

Efetch is a python web server, supports RESTful calls, and is built on top of dfVFS.

Efetch is in Beta and really needs the community's support, so please post any bugs. As far as this project is concerned, there is no such thing as a bad bug report.

For more information about efetch please see: https://github.com/maurermj08/efetch/wiki
