"""
Simple file browser
"""

from yapsy.IPlugin import IPlugin
import os


class FaBrowser(IPlugin):
    def __init__(self):
        self.display_name = 'Browser'
        self.popularity = 0
        self.parent = True
        self.cache = False
        self._default_child = 'fa_analyze/'
        IPlugin.__init__(self)

    def activate(self):
        IPlugin.activate(self)
        return

    def deactivate(self):
        IPlugin.deactivate(self)
        return

    def check(self, evidence, path_on_disk):
        """Checks if the file is compatable with this plugin"""
        return True

    def mimetype(self, mimetype):
        """Returns the mimetype of this plugins get command"""
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request, children, files=True, directories=True,
            evidence_item_plugin='fa_browser'):
        """Returns a formatted directory listing for the given path"""
        # If path is a folder just set the view to it, if not use the files parent folder
        if evidence['meta_type'] == 'Directory':
            curr_folder = evidence
        else:
            curr_folder = helper.db_util.get_file(evidence['image_id'], evidence['dir'])

        child_plugins = helper.get_children(evidence['image_id'], children)
        query_string = helper.get_query_string(request)
        filter_query = helper.get_filter(request)

        # If no child plugin specified uses the default in new tab
        if child_plugins:
            target = 'file_dir_frame'
            url = child_plugins
        else:
            url = self._default_child
            target = '_blank'

        listing = []
        evidence_items = helper.db_util.bool_query_evidence(curr_folder, filter_query)
        if directories and evidence['dir'] != '/':
            parent_dir = helper.db_util.get_file_from_pid(evidence['dir'][:-1])
            parent_dir['name'] = '..'
            evidence_items.append(parent_dir)

        for evidence_item in evidence_items:
            if (directories and evidence_item['meta_type'] == 'Directory') or (
                        files and evidence_item['meta_type'] == 'File'):
                listing.append('    <tr>')
                listing.append(
                    '        <td><img src="/plugins/fa_thumbnail/' + evidence_item['pid'] + '" alt="' + evidence_item[
                        'meta_type'] + '-' + evidence_item['ext'] + '" title="' + evidence_item['meta_type'] + '-' +
                    evidence_item['ext'] + '" style="width:32px;height:32px;"></td>')
                if evidence_item['meta_type'] == 'Directory':
                    listing.append(
                        '        <td><a href="/plugins/' + evidence_item_plugin + '/' + child_plugins + evidence_item[
                            'pid'] + query_string + '" target="_self">' + evidence_item['name'] + "</a></td>")
                else:
                    listing.append('        <td><a href="/plugins/' + url + evidence_item[
                        'pid'] + query_string + '" target="' + target + '">' + evidence_item['name'] + "</a></td>")
                if ('mtime' in evidence_item):
                    listing.append("        <td>" + evidence_item['mtime'] + "</td>")
                else:
                    listing.append("        <td> - </td>")
                if ('atime' in evidence_item):
                    listing.append("        <td>" + evidence_item['atime'] + "</td>")
                else:
                    listing.append("        <td> - </td>")
                if ('ctime' in evidence_item):
                    listing.append("        <td>" + evidence_item['ctime'] + "</td>")
                else:
                    listing.append("        <td> - </td>")
                if ('crtime' in evidence_item):
                    listing.append("        <td>" + evidence_item['crtime'] + "</td>")
                else:
                    listing.append("        <td> - </td>")
                if 'file_size' not in evidence_item:
                    listing.append("        <td> - </td>")
                elif isinstance(evidence_item['file_size'], list):
                    listing.append("        <td>" + str(evidence_item['file_size'][0]) + "</td>")
                else:
                    listing.append("        <td>" + str(evidence_item['file_size']) + "</td>")

                # if 'bookmark' not in evidence_item or evidence_item['bookmark'] == 'false':
                #    listing.append("        <td><img src='/reevidence_items/images/notbookmarked.png'></td>")
                # else:
                #    listing.append("        <td><img src='/reevidence_items/images/bookmarked.png'></td>")
                listing.append("    </tr>")

        # Creates HTML page
        html = ""
        curr_dir = os.path.dirname(os.path.realpath(__file__))

        if child_plugins:
            template = open(curr_dir + '/parent_browser_template.html', 'r')
            html = str(template.read())
            template.close()
            if str(children).startswith(evidence['image_id']):
                html = html.replace('<!-- Home -->', "/plugins/" + child_plugins + children + query_string)
            else:
                html = html.replace('<!-- Home -->', "/plugins/" + children + query_string)
        else:
            template = open(curr_dir + '/browser_template.html', 'r')
            html = str(template.read())
            template.close()

        html = html.replace('<!-- Table -->', '\n'.join(listing))
        return html
