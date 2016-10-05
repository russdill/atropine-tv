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

from PyQt4 import Qt
import sys
import datetime
import dateutil.tz
import effects
import tv_icon

localtz = dateutil.tz.tzlocal()

class program_info_widget(Qt.QFrame):
    def __init__(self, parent=None, name=None):
        super(program_info_widget, self).__init__(parent=parent)
        self.setObjectName(name)

        self.vchannel = None

        vbox = Qt.QVBoxLayout()
        hbox = Qt.QHBoxLayout()

        vbox.setSpacing(0)
        vbox.setMargin(12)

        self.header = Qt.QLabel()
        self.header.setFocusPolicy(Qt.Qt.NoFocus)
        self.header.setAlignment(Qt.Qt.AlignLeft | Qt.Qt.AlignTop)
        self.header.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Minimum)
        self.header.setMinimumWidth(1)
        self.header.setMinimumHeight(1)
        hbox.addWidget(self.header)

        self.times = Qt.QLabel()
        self.times.setFocusPolicy(Qt.Qt.NoFocus)
        self.times.setAlignment(Qt.Qt.AlignLeft | Qt.Qt.AlignRight)
        self.times.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Minimum)
        self.times.setMinimumWidth(1)
        self.times.setMinimumHeight(1)
        hbox.addWidget(self.times)
        vbox.addLayout(hbox, 0)

        self.description = Qt.QLabel()
        self.description.setWordWrap(True)
        self.description.setFocusPolicy(Qt.Qt.NoFocus)
        self.description.setAlignment(Qt.Qt.AlignLeft | Qt.Qt.AlignTop)
        self.description.setMinimumWidth(1)
        self.description.setMinimumHeight(1)
        self.description.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Expanding)
        vbox.addWidget(self.description, 1)

        self.setLayout(vbox)

    def set_program(self, time_sched):
        time, sched = time_sched

        if sched is None:
            self.header.setText("No schedule info")
            self.times.clear()
            self.description.clear()
            return

        text = sched.program.title

        subtitles = []
        if sched.program.syndicatedEpisodeNumber:
            #try:
            #    sep = int(sched.program.syndicatedEpisodeNumber)
            #    if sep > 100 and sep % 100:
            #        subtitles.append('S%d:E%d' % (sep / 100, sep % 100))
            #    else:
            #        subtitles.append(sched.program.syndicatedEpisodeNumber)
            #except:
            subtitles.append(sched.program.syndicatedEpisodeNumber)

        if sched.program.subtitle:
            subtitles.append('"%s"' % sched.program.subtitle)

        if subtitles:
            text += '<br><small>%s</small>' % ', '.join(subtitles)

        self.header.setText(text)

        start = time.strftime("%l:%M %p").strip()
        end_time = time + datetime.timedelta(minutes=sched.duration)
        end = end_time.strftime("%l:%M %p").strip()
        self.times.setText('%s - %s' % (start, end))

        descs = []
        if len(sched.program.crew):
            descs.append('<small>%s</small>' % ', '.join([x.fullname for x in sched.program.crew[:2]]))
        if sched.program.description:
            descs.append(sched.program.description)

        self.description.setText('<br>'.join(descs))

class station_logo_widget(Qt.QLabel):
    def __init__(self, parent):
        self.pixmap = None
        super(station_logo_widget, self).__init__(parent)
        self.setMinimumWidth(1)
        self.setMinimumHeight(1)

    def clear(self):
        self.pixmap = None
        super(station_logo_widget, self).setPixmap(tv_icon.pixmap(self.size()))

    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        if self.width() and self.height():
            super(station_logo_widget, self).setPixmap(self.pixmap.scaled(self.size(), Qt.Qt.KeepAspectRatio, Qt.Qt.SmoothTransformation))

    def resizeEvent(self, e):
        if self.width() and self.height():
            if self.pixmap is None:
                super(station_logo_widget, self).setPixmap(tv_icon.pixmap(self.size()))
            else:
                super(station_logo_widget, self).setPixmap(self.pixmap.scaled(self.size(), Qt.Qt.KeepAspectRatio, Qt.Qt.SmoothTransformation))
        super(station_logo_widget, self).resizeEvent(e)

# Makes it easier to find in the stylesheet
class station_info_widget(Qt.QLabel):
    def __init__(self, parent):
        super(station_info_widget, self).__init__(parent)

class station_info(object):
    def __init__(self, _parent, icon_manager, vchannels, delta=0):
        super(station_info, self).__init__()

        self.override = None
        self.callsign = ''
        self.vchannel = ''
        self.im = icon_manager
        self.vchannels = vchannels
        self.delta = delta

        self.info = station_info_widget(_parent)
        self.info.setFocusPolicy(Qt.Qt.NoFocus)
        self.info.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Minimum)
        self.info.setMinimumWidth(1)
        self.info.setMinimumHeight(1)

        self.icon = station_logo_widget(_parent)
        self.icon.setAlignment(Qt.Qt.AlignCenter)
        self.icon.setFocusPolicy(Qt.Qt.NoFocus)
        self.icon.setSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding)
        self.info.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Minimum)

    def set_override(self, text):
        self.override = text
        self.info.setText(self.override_text())

    def override_text(self):
        vc = self.override if self.override else self.vchannel
        return '<big>%s</big><br>%s' % (vc, self.callsign)

    def set_vchannel(self, vchannel):
        self.im.forget_label(self.icon)
        self.icon.clear()
        self.callsign = ''

        self.vchannel = vchannel

        if self.vchannel in self.vchannels.keys():
            if self.delta:
                idx = self.vchannels.keys().index(self.vchannel)
                idx = (idx + self.delta) % len(self.vchannels)
                self.vchannel = self.vchannels.keys()[idx]
            self.callsign = self.vchannels[str(self.vchannel)].station.callSign
            self.im.request(self.callsign, self.icon)
        self.info.setText(self.override_text())

    def new_guide(self):
        self.set_vchannel(self.vchannel)

class station_info_osd(station_info, Qt.QWidget):
    def __init__(self, parent, icon_manager, vchannels):
        super(station_info_osd, self).__init__(self, icon_manager, vchannels)
        self.setParent(parent)

        vbox = Qt.QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setMargin(0)

        self.info.setAlignment(Qt.Qt.AlignCenter)
        self.info.setAttribute(Qt.Qt.WA_TranslucentBackground)
        vbox.addWidget(self.info)

        self.icon.setAttribute(Qt.Qt.WA_TranslucentBackground)
        vbox.addWidget(self.icon)

        self.setLayout(vbox)

class station_info_guide_small(station_info, Qt.QObject):
    def __init__(self, parent, icon_manager, vchannels, delta=0):
        super(station_info_guide_small, self).__init__(parent, icon_manager, vchannels, delta)
        self.setParent(parent)

        self.info.setAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignVCenter)
        self.setParent(self.icon) # makes signals work

class station_info_guide_large(station_info, Qt.QWidget):
    def __init__(self, parent, icon_manager, vchannels, delta=0):
        super(station_info_guide_large, self).__init__(self, icon_manager, vchannels, delta)
        self.setParent(parent)

        vbox = Qt.QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setMargin(0)

        vbox.addWidget(self.icon)

        self.info.setAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignVCenter)
        vbox.addWidget(self.info)

        self.setLayout(vbox)

        dse = effects.QGraphicsBlurShadowEffect()
        dse.distance = 12
        dse.blurRadius = 24
        dse.color = Qt.QColor(0, 0, 0, 200)
        self.setGraphicsEffect(dse)

    def set_override(self, text):
        if text is None:
            self.icon.show()
        else:
            self.icon.hide()
        super(station_info_guide_large, self).set_override(text)

    def override_text(self):
        if self.override:
            return '<big>%s</big>' % self.override
        else:
            return '<big>%s</big><br>%s' % (self.vchannel, self.callsign)

class now_widget(Qt.QLabel):
    def __init__(self):
        super(now_widget, self).__init__()

        self.setFocusPolicy(Qt.Qt.NoFocus)
        self.timer = Qt.QTimer()
        self.timer.timeout.connect(self.update_time)
        self.update_time()

    def update_time(self):
        now = datetime.datetime.now(localtz)
        self.setText('<small>' + now.strftime("%l:%M %p").strip() + '</small>')
        delta = (now + datetime.timedelta(minutes=1)).replace(second=0,microsecond=0) - now
        self.timer.start(delta.total_seconds() * 1000.0)

class vchannel_input(Qt.QObject):
    active = Qt.pyqtSignal(str)
    aborted = Qt.pyqtSignal()
    done = Qt.pyqtSignal(str)

    def __init__(self, parent, vchannels):
        super(vchannel_input, self).__init__(parent)
        self.input = ''
        self.vchannels = vchannels
        self.timeout = 5.0
        self.timer = Qt.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timedout)

    def set_station_info(self, widget):
        self.active.connect(widget.set_override)
        self.aborted.connect(lambda x=None: widget.set_override(x))
        self.done.connect(lambda x=None: widget.set_override(None))

    def input_add(self, chr):
        self.timer.stop()
        self.input += str(chr)
        canidates = [c for c in self.vchannels.keys() if c.startswith(self.input)]
        if len(canidates) == 0:
            self.input = ''
            self.aborted.emit()
        elif len(canidates) == 1 and canidates[0] == self.input:
            vchannel = self.input
            self.input = ''
            self.done.emit(vchannel)
        else:
            self.timer.start(self.timeout * 1000)
            self.active.emit((self.input + '____')[:4])

    def timedout(self):
        vchannel = self.input
        self.input = ''
        if vchannel in self.vchannels:
            self.done.emit(vchannel)
        else:
            self.aborted.emit()

    def cancel(self):
        self.input = ''
        self.timer.stop()
        self.aborted.emit()
