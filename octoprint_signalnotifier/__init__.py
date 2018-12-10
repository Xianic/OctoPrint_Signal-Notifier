# coding=utf-8

from __future__ import absolute_import
import getpass
import octoprint.plugin
import os
import socket
import subprocess

class SignalNotifierPlugin(octoprint.plugin.EventHandlerPlugin,
                               octoprint.plugin.SettingsPlugin,
                               octoprint.plugin.AssetPlugin,
                               octoprint.plugin.TemplatePlugin):

    ## Helpers    
    def is_exe(self, fpath):
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            return True
        return False


    #~~ SettingsPlugin
    def get_settings_defaults(self):
        return dict(
            enabled=False,
            path="signal-cli",
            sender="",
            recipient="",
            message_format=dict(
                body="OctoPrint@{host}: Job complete: {filename} done printing after {elapsed_time}." 
            )
        )

    def get_settings_restricted_paths(self):
        return dict(admin=[["path"], ["sender"], ["recipient"]],
                    user=[["message_format", "body"]],
                    never=[])        

    def get_settings_version(self):
        return 1

    #~~ TemplatePlugin
    def get_template_configs(self):
        return [dict(type="settings", name="Signal Notifier", custom_bindings=False)]

    #~~ EventPlugin
    def on_event(self, event, payload):
        if event != "PrintDone":
            return
        
        if not self._settings.get(['enabled']):
            return
        
        filename = os.path.basename(payload["file"])

        import datetime
        import octoprint.util
        elapsed_time = octoprint.util.get_formatted_timedelta(datetime.timedelta(seconds=payload["time"]))

        tags = {'filename': filename, 
                'elapsed_time': elapsed_time,
                'host': socket.gethostname(),
                'user': getpass.getuser()}
        path = self._settings.get(["path"])
        sender = self._settings.get(["sender"])
        recipient = self._settings.get(["recipient"])
        message = self._settings.get(["message_format", "body"]).format(**tags)

        # check args and raise if not configured
        if not self.is_exe(path):
            # raise Exception("The path to signal-cli ('%s') doesn't point at an executable!" % path)
            self._logger.error("The path to signal-cli ('%s') doesn't point at an executable!" % path)
            return

        # TODO: check that sender is defined
        # TODO: check that recipient is defined
        # TODO: check that sender is in list of valid senders?

        # ./signal-cli -u +4915151111111 send -m "My first message from the CLI" +4915152222222
        # the_command = "%s -u %s send -m \"%s\" %s 2>&1" % (path, sender, message, recipient)
        the_args = [path, "-u", sender, "send -m", message, recipient]
        self._logger.debug("Command plugin will run is: '%s'" % ' '.join(the_args))
        osstdout = ""
        try:
            # call signal-cli
            osstdout = subprocess.check_call(the_args, stderr=subprocess.STDOUT)
        # TODO: catch subprocess.CalledProcessError vs generic error?
        except Exception as e:
            # report problem sending message
            self._logger.exception("Signal notification error: %s: %s" % (str(e), osstdout))
        else:
            # report notification was sent
            self._logger.info("Print notification sent to %s" % (self._settings.get(['recipient'])))

    ##~~ Softwareupdate hook
    def get_update_information(self):
        return dict(
            signalnotifier=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,
                current=self._plugin_version,

                # version check: github repository
                #type="github_release",
                type="github_commit",
                user="aerickson",
                repo="OctoPrint_Signal-Notifier",
                branch="master",

                # update method: pip
                # - release
                #pip="https://github.com/aerickson/OctoPrint_Signal-Notifier/archive/{target_version}.zip"
                # - master tarball
                pip="https://github.com/aerickson/OctoPrint_Signal-Notifier/archive/{target}.zip"
            )
        )

__plugin_name__ = "Signal Notifier"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SignalNotifierPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
