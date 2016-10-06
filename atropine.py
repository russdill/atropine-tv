#!/usr/bin/env python
#
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

import sys
import signal
import hdhomerun
import live
import guide
import guide_manager
import icon_manager
import callsign_manager
import configargparse
import collections
import xdg.BaseDirectory
import categories
import json
import os
import atomicwrites

import video_vlc
import source_hdhr

from PyQt4 import Qt


import faulthandler
faulthandler.enable()

"""
"""

class atropine(Qt.QStackedWidget):

    moved = Qt.pyqtSignal(Qt.QPoint)
    vchannel_changed = Qt.pyqtSignal(object)

    def __init__(self, options):
        super(atropine, self).__init__()
        self.vchannels = collections.OrderedDict()
        self.fullscreen = options.fullscreen

        gm = guide_manager.guide_manager(self, options)
        cm = callsign_manager.callsign_manager(self, options)
        im = icon_manager.icon_manager(cm, options)

	gm.new_guide.connect(cm.new_guide)
        gm.new_guide.connect(self.guide_update)

        self.vchannel = None
        self.channel_file = options.channel_file

        self.video = video_vlc.video_vlc()
        self.source = source_hdhr.source_hdhr(self.video)
        self.live = live.live(self, self.video, im, self.vchannels)
        self.guide = guide.guide_widget(self, options, self.video, im, self.vchannels)

        self.addWidget(self.live)
        self.addWidget(self.guide)

        self.video.setParent(self)
        self.video.show()

        self.setCurrentWidget(self.live)

        self.live.clicked.connect(lambda w=self.guide: self.setCurrentWidget(w))
        self.guide.done.connect(lambda w=self.live: self.setCurrentWidget(w))

        Qt.QTimer.singleShot(0, self.start)

        ss = """
            QWidget {
                border: none;
                background-color: rgb(60, 75, 90);
            }
            QLabel {
                font-family: sans-serif;
                font: 24pt;
                color: white;
            }
            video, video_proxy, guide_widget now_widget, time_header_widget {
                background-color: black
            }
            guide_widget station_logo_widget {
                background-color: rgb(150, 170, 190);
            }
            guide_widget program_info_widget {
                background-color: rgb(30, 30, 30);
                border: 2px solid black;
            }
            guide_widget program_info_widget QWidget {
                background-color: rgb(30, 30, 30);
            }
            guide_header_widget {
                background-color: darkblue;
            }
            station_info_guide_large QWidget {
                background-color: rgb(90, 105, 120);
            }
            info_widget, info_widget QWidget {
                background: none;
            }
            program_label {
                padding: 4px;
                border: 2px solid black;
            }
            program_label:focus {
                border: 6px solid white;
            }
            time_header_widget, now_widget {
                padding: 8px;
            }
            station_info_widget {
                padding: 6px;
            }
            osd_widget {
                margin: 50px;
            }
            guide_widget > station_info_widget {
                padding: 4px;
                font-size: 20pt;
            }
            QProgressBar {
                border: none;
                color: red;
            }
            QProgressBar::chunk {
                background-color: red;
            }
        """
        # https://raw.githubusercontent.com/MythTV/mythtv/master/mythtv/themes/default/categories.xml
        cc = categories.category_colors('categories.xml')
        for key, value in cc.iteritems():
            ss += 'QLabel[category="%s"] { background-color: rgb%s; }\n' % (key, str(value))

        self.setStyleSheet(ss)

    def start(self):
        try:
            with open(self.channel_file, 'r') as f:
                vchannel = f.read().strip()
                self._set_vchannel(vchannel)
        except:
            pass

    def _set_vchannel(self, vchannel):
        if self.vchannel == vchannel:
            return

        self.vchannel = vchannel
        self.source.set_vchannel(self.vchannel)
        self.vchannel_changed.emit(self.vchannel)

        if vchannel:
            try:
                with atomicwrites.atomic_write(self.channel_file, overwrite=True) as f:
                    f.write(self.vchannel)
            except:
                pass

    def set_vchannel(self, vchannel):
        if vchannel in self.vchannels.keys():
            self._set_vchannel(vchannel)
        self.setCurrentWidget(self.live)

    def guide_update(self, epg):
        self.vchannels.clear()
        self.vchannels.update(epg.mappings.values()[0].channels)

        vchannel = self.vchannel

        if vchannel not in self.vchannels.keys():
            if self.vchannels:
                vchannel = self.vchannels.keys()[0]
            else:
                vchannel = None

        self._set_vchannel(vchannel)

        self.live.new_guide()
        self.guide.new_guide()

    def keyPressEvent(self, e):
        if e.key() == Qt.Qt.Key_F11:
            if self.fullscreen:
                self.showNormal()
            else:
                self.showFullScreen()
            self.fullscreen = not self.fullscreen
        elif e.key() == Qt.Qt.Key_Escape:
            Qt.qApp.exit()
        else:
            super(atropine, self).keyPressEvent(e)

    def moveEvent(self, e):
        self.moved.emit(e.pos())

if __name__ == '__main__':

    paths = xdg.BaseDirectory.load_config_paths('atropine-tv')
    configs = [os.path.join(x, 'config') for x in paths]

    config = xdg.BaseDirectory.save_config_path('atropine-tv')
    iconmap = os.path.join(config, 'iconmap.xml')

    cache = xdg.BaseDirectory.save_cache_path('atropine-tv')
    sched = os.path.join(cache, 'sched.xml')
    channel = os.path.join(cache, 'channel.txt')


    parser = configargparse.ArgParser(default_config_files=configs,
               formatter_class=configargparse.DefaultsFormatter)
    parser.add('-c', '--config', is_config_file=True, help='Configuration file')
    parser.add('-u', '--username', type=str, required=True,
               help='Schedules Direct user name')
    parser.add('-p', '--password', type=str, required=True,
               help='Schedules Direct password')
    parser.add('-l', '--lineup-id', type=str,
               help='Schedules Direct lineup ID')
    parser.add('-s', '--sched', type=str, default=sched,
               help='Cached scheduler data')
    parser.add('-i', '--icons', type=str, default=cache,
               help='Icon cache directory')
    parser.add('-f', '--fullscreen', action='store_true',
               help='Start in full-screen mode')
    parser.add('--guide-rows', type=int, default=7,
               help='Number of program guide rows')
    parser.add('--guide-cols', type=int, default=5,
               help='Number of program guide columns')
    parser.add('-C', '--channel-file', type=str, default=channel,
               help='Location to store current channel')
    parser.add('--channel-resub', type=json.loads,
               help='Python re.sub actions for channel names in icon search')
    parser.add('--channel-drop', type=json.loads,
               help='Droppable tokens for channel names in icon search')
    parser.add('--channel-region', type=str, action='append',
               help='LyngSat Logo region (can be specified multiple times)')

    options = parser.parse_args()

    if options.channel_region is None:
        options.channel_region = ['us']

    Qt.QCoreApplication.setAttribute(Qt.Qt.AA_X11InitThreads)

    app = Qt.QApplication(sys.argv)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    widget = atropine(options)
    widget.resize(1920, 1080)
    if options.fullscreen:
        widget.showFullScreen()
    else:
        widget.showNormal()

    sys.exit(app.exec_())

