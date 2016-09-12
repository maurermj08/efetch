"""
Optical character recognition (OCR) for images using pytesseract

This plugin requires the following commands to be run:
    sudo apt-get install tesseract-ocr
    sudo pip install pytesseract
"""

import elasticsearch
import pytesseract
import logging
from bottle import abort
from yapsy.IPlugin import IPlugin
from PIL import Image


class FaImageOcr(IPlugin):

    def __init__(self):
        self.display_name = 'Image OCR'
        self.popularity = 3
        self.cache = True
        self.fast = False
        self.action = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        allowed_prefix = ['image']
        return str(evidence['mimetype'].split('/')[0]).lower() in allowed_prefix \
               and evidence['meta_type'] != 'Directory'

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        return '<xmp>' + helper.action_get(evidence, request, self.display_name, self.get_ocr_strings, 'image_ocr') + \
               '</xmp>'

    @staticmethod
    def get_ocr_strings(evidence):
        # This is the actual OCR call
        try:
            return pytesseract.image_to_string(Image.open(evidence['file_cache_path']))
        except:
            logging.warn('Failed to perform OCR on file "' + evidence['file_cache_path'] + '"')
            abort(400, 'It appears that the pathspec is for a file that the Tesseract cannot perform OCR on')

