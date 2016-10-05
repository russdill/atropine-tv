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

import vlc
import sys
import video

from PyQt4 import Qt

class video_vlc(video.video):
    def __init__(self):
        self.spu = None
        super(video_vlc, self).__init__()

        self.vlc = vlc.Instance('no-xlib')
        self.player = self.vlc.media_player_new()
        self.player.video_set_deinterlace('mean')
        self.events = self.player.event_manager()
        self.events.event_attach(vlc.EventType.MediaPlayerTimeChanged, self.time_changed, None)

        self.events.event_attach(vlc.EventType.MediaParsedChanged, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaMetaChanged, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaStateChanged, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaPlayerPlaying, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaPlayerPaused, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaPlayerStopped, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaPlayerTitleChanged, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaDiscovererStarted, self.changed, 1)
        self.events.event_attach(vlc.EventType.MediaDiscovererEnded, self.changed, 1)

        # The version control history (git log) says the following about the
        # Automatic mode (see commit f96b075043c421fb6466829a15ae0c8792b8ffe8)
        # The detection is based on the progressive/interlaced flags transported
        # at the codec level. As such, it is not really reliable (for 25fps at
        # least).
        # As soon as a picture is detected as interlaced, the configured
        # deinterlace mode is applied. After 30s of progressive video, the filter
        # is removed. The hysteresis helps with unreliable interlaced flags.

        if sys.platform.startswith('linux'):
            self.assign_winId = self.player.set_xwindow
        elif sys.platform == "win32":
            self.assign_winId = self.player.set_hwnd
        elif sys.platform == "darwin":
            self.assign_winId = self.player.set_nsobject
        else:
            raise Exception('Unsupported platform')

        self.assign_winId(self.winId())

    @vlc.callbackmethod
    def changed(self, data, data1):
        #print data, data1
        pass

    @vlc.callbackmethod
    def time_changed(self, data, data1):
        self.video_live()
        if self.spu:
            self.player.video_set_spu(self.spu)

    def set_spu(self, spu):
        super(video_vlc, self).set_spu(spu)
        self.player.video_set_spu(spu)

    def event(self, e):
        if e.type() == Qt.QEvent.WinIdChange:
            self.assign_winId(self.winId())
        return super(video_vlc, self).event(e)

    def play(self, mrl):
        self.video_restart()
        self.player.set_mrl(mrl, 'sout-mux-caching=100', 'network-caching=500')
        self.player.play()

    def stop(self):
        self.video_dead()
        self.player.stop()
