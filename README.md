# efetch
Evidence Fetcher (efetch) is a web-based file explorer and analyzer. Efetch supports viewing images, office documents, registries, PST files, sqlite databases, and more. Efetch supports navigating E01, Ex01, RAW, VHD, VMDK, ZIP, and more thanks to dfVFS.

After installation run the command **efetch** in the terminal and navigate to **localhost:8080** in a browser. Use the **expand** plugin to navigate into evidence files.

![alt tag](https://cloud.githubusercontent.com/assets/13810976/19025778/825659c6-88eb-11e6-988c-b16d28b1eae5.gif)

Efetch supports hundreds of file formats and can be easily extended with simple plugins. Below is an example of a simple efetch plugin:

```
  clamscan:
    name: Clam Scan
    command: "clamscan '{{ file_cache_path }}'"
```

Efetch is a python web server, supports RESTful calls, and is built on top of dfVFS.

Efetch is in Beta and really needs the community's support, so please post any bugs. As far as this project is concerned, there is no such thing as a bad bug report.

For more information about efetch please see: https://github.com/maurermj08/efetch/wiki
