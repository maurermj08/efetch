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
        self.popularity = 0
        self.cache = True
        self.fast = False
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
        index = helper.get_request_value(request, 'index', False)
        image_ocr = ''

        # Only needed when using elasticsearch just else just return the OCR
        if index:
            # If using elasticsearch get the first entry
            query = {'query': {'term': {'pathspec.raw': evidence['pathspec']}}}
            first_elastic_entry = helper.db_util.query_sources(query, index, 1)

            # If this plugin has not been run on this entry run it on all entries
            if 'image_ocr' not in first_elastic_entry:
                try:
                    image_ocr = self.get_ocr_strings(path_on_disk)
                    update = {'image_ocr': image_ocr}

                    print('scanning...')
                    events = elasticsearch.helpers.scan(helper.db_util.elasticsearch, query,
                                                        scroll=u'240m', size=10000)
                    for item in events:
                        print(str(item))
                        print('Updating...')
                        helper.db_util.update(item['_id'], index, update, doc_type=item['_type'])
                except:
                    logging.warn('Failed to update image_ocr in elasticsearch')
            else:
                image_ocr = first_elastic_entry['image_ocr']
        else:
            image_ocr = self.get_ocr_strings(path_on_disk)

        return '<xmp style="white-space: pre-wrap;">' + image_ocr + '</xmp>'

    def get_ocr_strings(self, path_on_disk):
        # This is the actual OCR call
        try:
            return pytesseract.image_to_string(Image.open(path_on_disk))
        except:
            logging.warn('Failed to perform OCR on file "' + path_on_disk + '"')
            abort(400, 'It appears that the pathspec is for a file that the Tesseract cannot perform OCR on')

