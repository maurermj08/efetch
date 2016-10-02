# efetch
Evidence Fetcher (efetch) is a web-based file explorer and analyzer.

Efetch supports hundreds of file formats and can be easily extended with simple plugins. Below is an example of a simple efetch plugin:

```
  clamscan:
    name: Clam Scan
    command: "clamscan '{{ file_cache_path }}'"
```

Efetch is a python web server, supports RESTful calls, and is built on top of dfVFS.

For more information please see: https://github.com/maurermj08/efetch/wiki
