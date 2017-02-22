# Copyright (C) 2016 Russ Dill <russ.dill@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import hdhomerun

from PyQt4 import Qt

class source_hdhr(Qt.QObject):
    def __init__(self, video, str_dev_ids=[]):

        super(source_hdhr, self).__init__(video)

        self.vchannel = None
        self.vchannels = dict()
        self.stations = dict()
        self.sel = None
        self.hdhr = None
        self.video = video
        self.assigned_target = None
        self.last_rescan = Qt.QElapsedTimer()

        self.proto = 'udp'
        self.port = 5000

        # Used for find a new hdhr tuner
        self.checks = 0
        self.timer = Qt.QTimer(self)
        self.timer.timeout.connect(self._timer_cb)
        self.dev_ids = []

        for str_dev_id in str_dev_ids:
            id, _, tuner = str_dev_id.partition('-')
            try:
                id = int(id, 0x10) if len(id) else None
            except:
                raise Exception('Unable to parse HDHomeRun id "%s"' % id)

            if id and not hdhomerun.HDHomerunDevice.validate_id(id):
                raise Exception('Invalid HDHomeRun id "%s"' % id)

            try:
                tuner = int(x) if len(tuner) else None
            except:
                raise Exception('Unable to parse tuner "%d"', tuners)
            self.dev_ids.append((id, tuner))

        if not len(self.dev_ids):
            # Default to search for all HDHRs and tuners
            self.dev_ids.append((None, None))

    def set_stations(self, stations):
        self.stations = stations

    def _timer_cb(self):
        self.timer_cb()

    def set_vchannel(self, vchannel, fcc_channel=None):

        if vchannel is None:
            # vchannel of None means stop running
            self.vchannel = None
            self.stop()
            return

        was = self.vchannel
        self.fcc_channel = fcc_channel
        self.vchannel = str(vchannel)

        if was == self.vchannel:
            # No action required
            pass

        else:
            if self.hdhr and not self.checks:
                self.program_vchannel()
            else:
                # We want to display something, find a tuner
                self.choose_hdhr()

    def stop(self, message=None):
        self.video.stop()
        self.video.status(message)
        self.timer.stop()
        self.vchannels = dict()
        if self.checks:
            self.hdhr = None

    def program_vchannel(self):
        # If it's just a new sub-program, select it instead
        if self.vchannel is not None:
            try:
                self.set_program()
                return
            except Exception as e:
                pass

        self.timer.stop()
        try:
            curr = self.hdhr.target
            self.ip = self.hdhr.local_ip
            name = self.hdhr.name

            new_target = '%s://%s:%d' % (self.proto, self.ip, self.port)

            if curr == 'none':
                curr = None
            if curr is not None and curr != new_target:
                # Lost abritration
                self.stop('Tuner in use by another host')
                self.choose_hdhr()
                return

            self.video.play('%s://@%s:%d' % (self.proto, self.ip, self.port))

            try:
                self.hdhr.set('/tuner%d/vchannel' % self.hdhr.tuner, self.vchannel)
                self.program_set = True
            except:
                self.hdhr.set('/tuner%d/channel' % self.hdhr.tuner, self.fcc_channel)
                self.program_set = False

            was_playing = self.assigned_target
            self.assigned_target = new_target
            self.hdhr.target = new_target
            self.vchannels = dict()

            self.timer_cb = self.monitor
            self.timer.start(100)
            self.ticks = 0
            if not was_playing:
                self.video.status('Tuner %s selected' % name)

        except RuntimeError as e:
            e = str(e)
            self.stop(e)
            if e == 'Communication error':
                # TCP socket died, find another tuner
                self.choose_hdhr()
            elif e == 'ERROR: invalid virtual channel':
                # illegal vchannel selected
                self.vchannel = None
            else:
                # unknown tuning error
                self.vchannel = None

    def set_vchannels(self):
        info = str(self.hdhr.streaminfo)
        self.vchannels = dict()
        for line in info.splitlines():
            program, _, line = line.partition(':')
            if _ != ':':
                continue
            line = line.strip()
            vchannel, _, name = line.partition(' ')
            # hdhomerun returns a list of vchannels with 0 until it has data
            if vchannel == '0':
                continue
            self.vchannels[vchannel] = program

    def set_program(self):
        if self.vchannel not in self.vchannels:
            raise Exception('Invalid ch. mapping')
        self.video.play('%s://@%s:%d' % (self.proto, self.ip, self.port))

        program = self.vchannels[self.vchannel]
        self.hdhr.set('/tuner%d/program' % self.hdhr.tuner, program)

    def monitor(self):
        try:
            target = self.hdhr.target
            status = self.hdhr.status
            vstatus = self.hdhr.vstatus
        except RuntimeError as e:
            # TCP socket died
            self.stop(str(e))
            self.choose_hdhr()
            return

        if target == 'none':
             target = None

        if target is None:
            # Streaming stopped, restart
            self.hdhr.target = self.assigned_target
            self.video.play('%s://@%s:%d' % (self.proto, self.ip, self.port))

        elif target != self.assigned_target:
            # Lost arbitration
            self.stop('Tuner in use by another')
            self.choose_hdhr()

        elif (not status['signal'] or not status['locked']) and self.ticks > 20:
            # No signal, keep monitoring...
            self.video.status('No signal')
            self.timer.start(100)

        elif vstatus['not_subscribed']:
            # No access
            self.stop('Not subscribed')
            self.vchannel = None

        elif not status['pps'] and self.ticks > 20:
            # Streaming has stopped, arbitration lost?
            self.stop('Streaming lost')
            self.choose_hdhr()

        else:
            try:
                if not self.vchannels:
                    self.set_vchannels()
                    if not self.vchannels and self.ticks > 20:
                        raise Exception('Invalid vchannel')
                elif not self.program_set:
                    self.set_program()
                    self.program_set = True
            except Exception as e:
                self.stop(str(e))
                self.choose_hdhr()
            self.program_set = True

            # Ok, keep monitoring
            self.timer.start(100)

        self.ticks += 1

    def choose_hdhr(self):
        self.assigned_target = None

        if self.sel is None:
            self.last_rescan.start()
            self.sel = hdhomerun.HDHomerunDeviceSelector()

            for dev_id in self.dev_ids:
                id, tuner = dev_id
                devs = hdhomerun.HDHomerunDevice.find_devices(id=id)
                devs = [x for x in devs if tuner is None or x.tuner == tuner]
                self.sel.extend(devs)
            self.tuner_count = len(self.sel)

        self.hdhr = self.sel.choose_and_lock()
        if self.hdhr:
            # Found a suitable tuner, test it
            self.hdhr.unlock() # Allow other consumers (MythTV) to override
            self.sel.remove(self.hdhr)
            self.checks = 5
            self.check_hdhr()
            return

        # No suitible tuner found
        self.timer_cb = self.choose_hdhr
        self.sel = None

        # Only rescan up to once every 10 seconds
        remaining = 10 * 1000 - self.last_rescan.elapsed()
        if remaining > 0:
            # We are looping through all the tuners in under 10 seconds, let
            # the user know something is up
            if self.tuner_count:
                self.video.status('All tuners busy')
            else:
                self.video.status('No tuners found')
        else:
           remaining = 0

        self.timer.start(remaining)

    def check_hdhr(self):
        try:
            status = self.hdhr.status
        except:
            # TCP socket died, try another
            self.hdhr = None
            self.timer_cb = self.choose_hdhr
            self.timer.start(100)
            return

        if status['pps']:
            # In use, try another
            self.hdhr = None
            self.timer_cb = self.choose_hdhr
            self.timer.start(100)
        elif self.checks:
            # still testing...
            self.checks -= 1
            self.timer_cb = self.check_hdhr
            self.timer.start(100)
        else:
            # Tuner is free, yay
            self.program_vchannel()
