"""
AJAX for PST Viewer plugin
"""

from yapsy.IPlugin import IPlugin
from flask import Response, jsonify
import json
import logging
import pypff
import sys

class FaPstviewAjax(IPlugin):
    def __init__(self):
        self.display_name = 'Pstview Ajax'
        self.popularity = 0
        self.cache = True
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatible with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "application/json"

    def get(self, evidence, helper, path_on_disk, request):
        """Returns the result of this plugin to be displayed in a browser"""
        method = helper.get_request_value(request, 'method')

        if not method:
            # TODO CHANGE ERROR
            logging.error('Method required')
            raise IOError
        elif method == "base":
            return self.base_tree(path_on_disk)
        elif method == "children":
            return self.get_children(request, helper, path_on_disk)
        elif method == "values":
            return self.values(request, helper, path_on_disk)

        # TODO CHANGE ERROR
        logging.error('Unknown method "' + method + '" provided')
        raise IOError


    def base_tree(self, path_on_disk):
        data = self.get_sub_messages("", path_on_disk)
        # TODO REPLACE WITH DICTIONARY AND JSONIFY, SEE: http://stackoverflow.com/questions/12435297/how-do-i-jsonify-a-list-in-flask
        return Response(json.dumps(data), mimetype='application/json')

    def get_children(self, request, helper, path_on_disk):
        path = unicode(helper.get_request_value(request, 'key'))
        if path.endswith('/'):
            path = path[:-1]
        data = self.get_sub_messages(path, path_on_disk)
        # TODO REPLACE WITH DICTIONARY AND JSONIFY, SEE: http://stackoverflow.com/questions/12435297/how-do-i-jsonify-a-list-in-flask
        return Response(json.dumps(data), mimetype='application/json')

    def values(self, request, helper, path_on_disk):
        path,key = unicode(helper.get_request_value(request, 'key')).rsplit('/', 1)
        if not key:
            #No key means it is a folder and currently no support for displaying folder information
            return
        key = int(key)

        pst = get_pst(path_on_disk)
        msg = self.get_directory(path, pst).get_sub_message(key)

        return jsonify({'subject': msg.get_subject().encode("UTF-8"),
                'message': msg.get_plain_text_body().encode("UTF-8")})

    def get_directory(self, path, pst):
        if pst.get_root_folder().get_display_name():
            new_path = "" + u"/" + unicode(pst.get_root_folder().get_display_name())
        else:
            new_path = ""
        if path == new_path:
            return pst.get_root_folder()
        return self.get_sub_directory(path, pst.get_root_folder(), new_path)

    def get_sub_directory(self, path, directory, curr_path = ""):
        for i in range(0, directory.get_number_of_sub_folders()):
            if directory.get_sub_folder(i).get_display_name():
                new_path = curr_path + u"/" + unicode(directory.get_sub_folder(i).get_display_name())
            else:
                new_path = curr_path
            if unicode(path) == unicode(new_path):
                return directory.get_sub_folder(i)
            if path.startswith(new_path):
                return self.get_sub_directory(path, directory.get_sub_folder(i), new_path)

    def get_sub_messages(self, path, path_on_disk):
        pst = get_pst(path_on_disk)
        directory = self.get_directory(path, pst)

        pst_nodes = []

        #Append Messages
        for i in range(0, directory.get_number_of_sub_messages()):
            msg = directory.get_sub_message(i)
            try:
                pst_nodes.append({'title': msg.get_subject().encode("UTF-8"),
                           'key': path + '/' + str(i),
                           'folder': False,
                           'lazy': False
                           } )
            except:
                e = sys.exc_info()[0]
                logging.warn('Failed to parse PST message due to error %s', e)

        #Append Folders
        for i in range(0, directory.get_number_of_sub_folders()):
            pst_nodes.append({'title': unicode(directory.get_sub_folder(i).get_display_name()),
                          'key': path + u"/" + unicode(directory.get_sub_folder(i).get_display_name()) + u"/",
                          'folder': True,
                          'lazy': directory.get_sub_folder(i).get_number_of_sub_folders() > 0 or
                                  directory.get_sub_folder(i).get_number_of_sub_messages() > 0
                          })
        return pst_nodes

def get_pst(path_on_disk):
    pst = pypff.file()
    pst.open(path_on_disk)
    return pst