# Play a sound with shell command via gcode
#
# Copyright (C) 2019  Eric Callahan <arksine.code@gmail.com>
#
# Modified for sound by Matti Rasanen <>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os
import shlex
import subprocess
import logging

class ShellCommand:
    def __init__(self, config):
        self.name = config.get_name().split()[-1]
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        sid = config.get('path')
        sid = os.path.expanduser("aplay %s" % sid)
        self.path = shlex.split(sid)
        self.timeout = config.getfloat('timeout', 2., above=0.)
        self.verbose = config.getboolean('verbose', False)
        self.proc_fd = None
        self.partial_output = ""
        self.gcode.register_mux_command(
            "PLAY_SOUND", "SID", self.name,
            self.sid_PLAY_SOUND,
            desc=self.sid_PLAY_SOUND_help)

    def _process_output(self, eventime):
        if self.proc_fd is None:
            return
        try:
            data = os.read(self.proc_fd, 4096)
        except Exception:
            pass
        data = self.partial_output + data.decode()
        if '\n' not in data:
            self.partial_output = data
            return
        elif data[-1] != '\n':
            split = data.rfind('\n') + 1
            self.partial_output = data[split:]
            data = data[:split]
        else:
            self.partial_output = ""
        self.gcode.respond_info(data)

    sid_PLAY_SOUND_help = "Play a sound trough a linux shell command. Specify only a path for the sound file(.WAV). APLAY must be installed and pi configured for sound."
    def sid_PLAY_SOUND(self, params):
    #def sid_PLAY_SOUND():
        #gcode_params = params.get('PARAMS','')
        #gcode_params = shlex.split(gcode_params)
        reactor = self.printer.get_reactor()
        #self.gcode.respond_info("Command: {%s}:" % (self.path))
        try:
            proc = subprocess.Popen(
                #self.path + gcode_params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                self.path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception:
            logging.exception(
                "play_sound: sound ID {%s} failed" % (self.name))
            raise self.gcode.error("Error playing sound {%s}" % (self.name))
        if self.verbose:
            self.proc_fd = proc.stdout.fileno()
            #self.gcode.respond_info("Playing sound {%s}...:" % (self.name))
            hdl = reactor.register_fd(self.proc_fd, self._process_output)
        eventtime = reactor.monotonic()
        endtime = eventtime + self.timeout
        complete = False
        while eventtime < endtime:
            eventtime = reactor.pause(eventtime + .05)
            if proc.poll() is not None:
                complete = True
                break
        if not complete:
            proc.terminate()
        if self.verbose:
            if self.partial_output:
                self.gcode.respond_info(self.partial_output)
                self.partial_output = ""
            if complete:
                return
                #msg = "Sound {%s} finished!\n" % (self.name)
            else:
                msg = "Sound {%s} timed out" % (self.name)
            self.gcode.respond_info(msg)
            reactor.unregister_fd(hdl)
            self.proc_fd = None


def load_config_prefix(config):
    return ShellCommand(config)
