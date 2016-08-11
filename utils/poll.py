import logging
import os
import threading
import time


class Poll(threading.Thread):
    """This class polls the YAML plugin file for changes"""

    def __init__(self, EfetchPluginManager, interval=3):
        self._interval = interval
        self._last_timestamp = 0
        self._plugin_manager = EfetchPluginManager
        self.stop = False
        threading.Thread.__init__(self)

    def run(self):
        """Polls the plugin file based on modification time and reloads plugins if there is a change"""
        while not self.stop:
            current_timestamp = os.stat(self._plugin_manager.plugins_file).st_mtime
            if current_timestamp != self._last_timestamp:
                logging.info(u'Plugin YAML file updated')
                self._last_timestamp = current_timestamp
                self._plugin_manager.reload_plugins_file()
            time.sleep(self._interval)
