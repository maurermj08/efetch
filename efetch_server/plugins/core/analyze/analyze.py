"""
Basic UI for browsing and analyzing files
"""

from yapsy.IPlugin import IPlugin
from flask import render_template_string
import logging


TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/themes/default/easyui.css">
    <link rel="stylesheet" type="text/css" href="/static/themes/{{ theme }}/easyui.css">
    <link rel="stylesheet" href="/static/font-awesome/css/font-awesome.min.css">
    <meta http-equiv="content-type" content="text/html; charset=us-ascii" />
    <script src="/static/jquery-1.11.3.min.js"></script>
    <script type="text/javascript" src="/static/jquery.easyui.min.js"></script>

    <style>
        #nav {
            line-height:30px;
            height:100%;
            width:400px;
            float:left;
            padding:0px;
        }
        .panel-body {
            font-size: inherit; !important
        }
        .layout-button-left {
            padding-left: 0px; !important
        }
        html{
            height: 100%;
        }
        body {
            min-height: 100%;
            margin: 0px;
            background-color: white;
        }
        a {
            display:block;
            color: #FFFFFF;
            padding-top: 5px;
            padding-bottom: 5px;
            text-decoration: none;
            font-weight: bold;
            text-transform: uppercase;
            text-align: center;
            font-size: 14px;
        }
        a:hover, a:active {
            color: rgb(153, 193, 255);
        }
        p {
            line-height:20px;
            color: #FFFFFF;
            padding-left: 1px;
            text-decoration: initial;
            margin:0
        }
        #nav {
            line-height:20px;
            background-color:#414244;
            height:100%;
            width:100%;
            float:left;
            font-family: Arial, Helvetica, sans-serif;
        }
        #iframe {
            top: 0px;
            right: 0px;
            height: 100%;
            width: 100%;
            border: none;
            background-color: white;
        }

    </style>
    <title>Analyze</title>
</head>

<body>
        <div class="easyui-layout" style="width:100%;height:100%;">
            <div data-options="region:'west',hideCollapsedContent:false,split:true" title="Plugins" style="width:200px;background-color: #414244;">
            <div id="nav">
                <p><b>
                    {{ evidence.file_name }}
                </b><br /></p>
                <p align="right">
                    {{ evidence.mimetype }}
                <br />
                    {{ evidence.size }} Bytes
                <br /></p>
                <hr />
                <br />
                <a href="/plugins/overview?{{ evidence.url_query }}" target="frame">
                    <i class="fa fa-info-circle" style="font-size:24px;padding-bottom:5px"></i><br>Information
                </a>
                <br>
                    {% for plugin in plugins %}
                        <a href="/plugins/{{ plugin.name }}?{{ evidence.url_query }}" target="frame">
                            <i class="fa {{ plugin.icon }}" style="font-size:24px;padding-bottom:5px"></i><br>
                            {{ plugin.display_name }}
                        </a><br>
                    {% endfor %}
                </div>
            </div>
            <div data-options="region:'center',title:''">
                <iframe name="frame" id="iframe" src="/plugins/overview?{{ evidence.url_query }}"></iframe>
            </div>
        </div>
</body>
</html>
"""


class Analyze(IPlugin):
    def __init__(self):
        self.display_name = 'File Analyze'
        self.popularity = 0
        self.cache = False
        self.fast = False
        self.action = False
        self.ignore_loader = ['preview', 'fa_timeline']
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
        return "text/plain"

    def get(self, evidence, helper, path_on_disk, request):
        """Provides a web view with all applicable plugins, defaults to most popular"""

        if evidence['meta_type'] =='File' and not evidence['mimetype_known']:
            evidence['mimetype'] = helper.pathspec_helper.get_mimetype(evidence['pathspec'])
            evidence['mimetype_known'] = True

        # Add Directoy link
        plugins = []

        size = evidence.get('size', 0)
        if isinstance(size, list):
            size = size[0]

        # Order Plugins by populatiry from highest to lowest
        for pop in reversed(range(1, 11)):
            for plugin_name in helper.plugin_manager.get_all_plugins():
                plugin = helper.plugin_manager.get_plugin_by_name(plugin_name)
                if plugin.popularity == pop:
                    # Check if plugin applies to curr file
                    if plugin.display_name != 'Overview' and \
                            plugin.check(evidence, evidence['file_cache_path']) and \
                            (not plugin.cache or int(size) <= helper.max_file_size):
                        logging.debug("Check matched, adding plugin " + plugin.display_name)
                        plugins.append({
                           'icon': getattr(plugin, 'icon', 'fa-file-o'),
                           'name': plugin_name,
                           'display_name': getattr(plugin, 'display_name', plugin_name)
                        })
                    else:
                        logging.debug("Check did not match, NOT adding plugin " + plugin_name)

        theme = 'black'
        home = '/plugins/overview?' + evidence['url_query']

        # Modifies HTML
        return render_template_string(TEMPLATE, evidence=evidence, theme=theme, plugins=plugins, home=home)