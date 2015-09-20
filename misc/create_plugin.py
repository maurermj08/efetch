#/usr/bin/python

import sys
import os

global name
global display
global author
global description
global cname
global check
global get
global imports

def main(argv):
    global name
    global display
    global author
    global description
    global cname
    global check
    global get
    global imports
    
    name = ""
    author = ""
    description = ""
    cname = ""
    popularity = 5
    check = "return True"
    get = 'return \'<xmp style="white-space: pre-wrap;">TODO</xmp>\''
    imports = []

    print("Efetch Plugin Maker")
    print("")
    get_name()
    get_display()
    get_author()
    get_description()
    get_popularity()
    get_imports()
    get_check()
    #get_get()

    print("Name:        " + name)
    print("Camel Name:  " + cname)
    print("Display:     " + display)
    print("Author:      " + author)
    print("Description: " + description)
    print("Popularity:  " + str(popularity))
    print("Imports:     " + ",".join(imports))
    print("check:       " + check)
    #print("Get:         " + get)

    curr_dir = os.path.dirname(os.path.realpath(__file__))
    
    #Python
    template = open(curr_dir + '/plugin_template.txt', 'r')
    plugin = str(template.read())
    plugin = plugin.replace("%{description}", description)
    plugin = plugin.replace("%{cname}", cname)
    plugin = plugin.replace("%{popularity}", str(popularity))
    plugin = plugin.replace("%{check}", check)
    plugin = plugin.replace("%{get}", get)
    plugin = plugin.replace("%{import}", "\n".join(imports))
    plugin = plugin.replace("%{display}", display)
    plugin = plugin.replace("%{desription}",description)
    print(plugin)

    print("")
    print("")
    print("")

    template_yp = open(curr_dir + '/plugin_yapsy_template.txt', 'r')
    yapsy = str(template_yp.read())
    yapsy = yapsy.replace("%{name}", name)
    yapsy = yapsy.replace("%{author}", author)
    yapsy = yapsy.replace("%{description}", description)
    print(yapsy)

    if os.path.isfile(curr_dir + "/" + name + ".py"):
        print("ERROR: File " + name + ".py already exsists")
        sys.exit(1)
    if os.path.isfile(curr_dir + "/" + name + ".yapsy-plugin"):
        print("ERROR: File " + name + ".yapsy-plugin already exsists")
        sys.exit(1)

    new_plugin = open(curr_dir + "/" + name + ".py", 'a')
    new_plugin.write(plugin)
    new_plugin.close()

    new_yapsy = open(curr_dir + "/" + name + ".yapsy-plugin", 'a')
    new_yapsy.write(yapsy)
    new_yapsy.close()

def get_name():
    global name
    global cname
    raw = str(raw_input("Plugin name (i.e fa_strings): "))
    name = raw.lower().replace(" ", "_")
    cname = raw.replace("_", " ").title().replace(" ", "")

def get_display():
    global display
    display = raw_input("Display name (i.e. 'Strings', 'Hex View', 'Adv. Preview'): ")

def get_author():
    global author
    author = raw_input("Your name (i.e. John Doe): ")

def get_description():
    global description
    description = raw_input("1 Line Description (i.e. 'Gets Strings from a file'): ")

def get_popularity():
    global popularity
    try:
        popularity = int(raw_input("Popularity, 0(Hidden) 1(low) - 10(high): "))
    except:
        popularity = 5

def get_imports():
    global imports
    raw = raw_input("Imports, blank when done (i.e. 'os'): ")
    if raw:
        imports.append("import " + raw)
        get_imports()

def get_check():
    global check
    print("1 - None")
    print("2 - File Type")
    print("3 - Size")
    print("4 - Mimetype")
    print("5 - File Type and Size")
    print("6 - File Type and MimeType")
    print("7 - Size and Mimetype")
    print("8 - File Type, Size, and MimeType")
    answer = 0
    while answer < 1 or answer > 8:
        try:
            answer = int(raw_input("Answer: "))
        except:
            answer = 0

def get_get():
    global get
    get = raw_input("Get: ")

if __name__=="__main__":
        main(sys.argv[1:])
