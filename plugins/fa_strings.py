"""
A simple plugin that takes a file and returns the Strings in it
"""

from yapsy.IPlugin import IPlugin

class FaStrings(IPlugin):

	#Max size is 100 MB
	maxsize = 100000000 
	
	#Mime type is just text
	plugin_mimetype = "text/plain"
	
	def __init__(self):
		IPlugin.__init__(self)

	def activate(self):
		IPlugin.activate(self)
		return

	def deactivate(self):
		IPlugin.deactivate(self)
		return

	def display_name(self):
		"""Returns the name displayed in the webview"""
		return "Strings"

	def check(self, mimetype, size):
		"""Checks if the file is compatable with this plugin"""
		if (size < maxsize):
			return False
		else:
			return True

	def mimetype(self):
		"""Returns the mimetype of this plugins get command"""
		return plugin_mimetype

	def get(self, input_file, full_path, mimetypoe, size):
		"""Returns the result of this plugin to be displayed in a browser"""
		strings = list(self.get_file_strings(input_file))
		return "\n".join(strings)		

	def get_file_strings(input_file, min=4):
        	result = ""
        	for c in input_file.read():
            		if c in string.printable:
            	    		result += c
                		continue
            		if len(result) >= min:
                		yield result
            		result = ""
