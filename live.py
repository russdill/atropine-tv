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

import video
import live
import guide
import info
import monotonic
import effects
import datetime
import dateutil.tz
from PyQt4 import Qt

localtz = dateutil.tz.tzlocal()

class osd_widget(Qt.QLabel):
    def __init__(self, parent):
        super(osd_widget, self).__init__(parent, Qt.Qt.ToolTip)

        self.setFocusPolicy(Qt.Qt.NoFocus)
        self.setAttribute(Qt.Qt.WA_TranslucentBackground)
        self.setAlignment(Qt.Qt.AlignVCenter | Qt.Qt.AlignRight)
        self.hide()

        dse = effects.QGraphicsBlurShadowEffect()
        dse.distance = 4
        dse.blurRadius = 8
        dse.color = Qt.QColor(0, 0, 0)
        self.setGraphicsEffect(dse)

        self.timer = Qt.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def display(self, text):
        self.setText('<h1>' + text + '</h1>')
        self.show()
        self.timer.start(5000)

class shade_widget(Qt.QWidget):
    def __init__(self, parent):
        super(shade_widget, self).__init__(parent, Qt.Qt.ToolTip)
        self.setFocusPolicy(Qt.Qt.NoFocus)
        self.opacity = 0.8
        self.setWindowOpacity(self.opacity)

class info_widget(Qt.QWidget):
    tune = Qt.pyqtSignal(str)

    def __init__(self, parent, icon_manager, vchannels):

        self.fade = None
        self.fade_time = 0.2
        self.dialog_time = 8.0
        self.height = 294
        self.vchannel = None
        self.vchannels = vchannels

        super(info_widget, self).__init__(parent, Qt.Qt.ToolTip)

        self.setFocusPolicy(Qt.Qt.NoFocus)
        self.setAttribute(Qt.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1.0)
        self.setFixedHeight(self.height)

        self.timer = Qt.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timeout)

        self.prog_timer = Qt.QTimer()
        self.prog_timer.setSingleShot(True)
        self.prog_timer.timeout.connect(self.next_prog)

        self.shade_widget = shade_widget(parent)

        hbox = Qt.QHBoxLayout(self)

        self.info = info.station_info_osd(self, icon_manager, vchannels)
        hbox.addWidget(self.info, 16)

        vbox = Qt.QVBoxLayout()

        now_label = info.now_widget()
        now_label.setAttribute(Qt.Qt.WA_TranslucentBackground)
        vbox.addWidget(now_label, 0)

        self.pos = Qt.QProgressBar(self)
        self.pos.setMaximum(100)
        self.pos.textVisible = False
        self.pos.setAttribute(Qt.Qt.WA_TranslucentBackground)
        self.pos.setFixedHeight(5)
        vbox.addWidget(self.pos, 0)

        self.desc = info.program_info_widget(self, 'live')
        vbox.addWidget(self.desc, 1)

        hbox.addLayout(vbox, 100)
        self.setLayout(hbox)

        self.channel_input = info.vchannel_input(self, vchannels)
        self.channel_input.set_station_info(self.info)
        self.channel_input.active.connect(self.popup)

    def timeout(self):
        if self.fade is not None:
            delta = monotonic.monotonic() - self.fade
            if delta > self.fade_time:
                self.fade = None
                self.hide()
            else:
                self.shade_widget.setWindowOpacity(self.shade_widget.opacity * (1.0 - delta / self.fade_time))
                self.setWindowOpacity(1.0 * (1.0 - delta / self.fade_time))
                self.timer.start(10)
        else:
            self.fade = monotonic.monotonic()
            self.timer.start(10)

    def popup(self):
        self.fade = None
        self.shade_widget.setWindowOpacity(self.shade_widget.opacity)
        self.setWindowOpacity(1.0)
        self.timer.start(self.dialog_time * 1000)

    def input_add(self, chr):
        self.channel_input.input_add(chr)

    def resizeEvent(self, e):
        super(info_widget, self).resizeEvent(e)
        self.shade_widget.resize(e.size())

    def hideEvent(self, e):
        super(info_widget, self).hideEvent(e)
        self.timer.stop()
        self.prog_timer.stop()
        self.channel_input.cancel()
        self.shade_widget.hide()

    def showEvent(self, e):
        super(info_widget, self).showEvent(e)
        self.shade_widget.show()
        self.next_prog()
        self.raise_()
        self.popup()

    def moveEvent(self, e):
        super(info_widget, self).moveEvent(e)
        self.shade_widget.move(e.pos())

    def new_guide(self):
        if self.isVisible():
            self.info.new_guide()
            self.next_prog()

    def next_prog(self):
        if self.vchannel not in self.vchannels.keys():
            self.desc.set_program((None, None))
            return

        sched = self.vchannels[str(self.vchannel)].station.schedule.entries
        sched_entry = None
        now = datetime.datetime.now(localtz)
        next_is_last = False
        next_wake = None
        sched_time = None
        for start, entry in sched.iteritems():
            end = start + datetime.timedelta(minutes=entry.duration)
            if end > now and start <= now:
                sched_entry = entry
                sched_time = start
                next_wake = end
                break
            if next_is_last:
                next_wake = start
                break
            if start >= end:
                next_is_last = True
        self.desc.set_program((sched_time, sched_entry))
        if next_wake:
            self.prog_timer.start((next_wake - now).total_seconds() * 1000)
        else:
            self.prog_timer.stop()

        if sched_time:
            self.pos.setValue(100.0 * (now - sched_time).total_seconds() / (next_wake - sched_time).total_seconds())
            self.pos.show()
        else:
            self.pos.hide()

    def set_vchannel(self, vchannel):
        self.vchannel = vchannel
        self.info.set_vchannel(vchannel)
        self.popup()
        self.show()
        self.next_prog()


class live(video.video_proxy):
    clicked = Qt.pyqtSignal()

    def __init__(self, parent, video_widget=None, icon_manager=None, vchannels=None):
        self.vchannel = parent.vchannel
        self.last = None

        super(live, self).__init__(parent, video_widget)

        self.vchannels = vchannels
        self.parent = parent

        self.info_widget = info_widget(self, icon_manager, vchannels)
        self.info_widget.channel_input.done.connect(self.parent.set_vchannel)
        parent.vchannel_changed.connect(self.info_widget.set_vchannel)
        parent.vchannel_changed.connect(self.set_vchannel)

        self.setMinimumHeight(self.info_widget.height * 2)
        self.setMinimumWidth(self.info_widget.height * 2 * 16 / 9)

        self.osd = osd_widget(parent)

        parent.moved.connect(self.moved)

    channel_keys = [
        Qt.Qt.Key_0,
        Qt.Qt.Key_1,
        Qt.Qt.Key_2,
        Qt.Qt.Key_3,
        Qt.Qt.Key_4,
        Qt.Qt.Key_5,
        Qt.Qt.Key_6,
        Qt.Qt.Key_7,
        Qt.Qt.Key_8,
        Qt.Qt.Key_9,
        Qt.Qt.Key_Period,
        Qt.Qt.Key_Underscore
    ]

    def resizeEvent(self, e):
        super(live, self).resizeEvent(e)
        x = e.size().width()
        y = e.size().height()
        self.info_widget.move(self.mapToGlobal(Qt.QPoint(0, y - self.info_widget.height)))
        self.info_widget.setFixedWidth(x)

        self.osd.move(self.mapToGlobal(Qt.QPoint(0, 0)))
        self.osd.setFixedWidth(x)

    def hideEvent(self, e):
        super(live, self).hideEvent(e)
        self.info_widget.hide()

    def showEvent(self, e):
        super(live, self).showEvent(e)
        self.info_widget.show()
        self.setFocus()

    def moved(self, p):
        x = self.size().width()
        y = self.size().height()
        self.info_widget.move(self.mapToGlobal(Qt.QPoint(0, y - self.info_widget.height)))
        self.osd.move(self.mapToGlobal(Qt.QPoint(0, 0)))

    def vchannel_incdec(self, incdec):
        if self.vchannel in self.vchannels.keys():
            idx = self.vchannels.keys().index(self.vchannel) + incdec
            idx %= len(self.vchannels)
            self.parent.set_vchannel(self.vchannels.keys()[idx])

    def set_vchannel(self, vchannel):
        if self.vchannel != vchannel and vchannel != None:
            self.last = self.vchannel
            self.vchannel = vchannel

    def new_guide(self):
        if self.last not in self.vchannels.keys():
            self.last = None
        self.info_widget.new_guide()

    def keyPressEvent(self, e):
        if e.key() == Qt.Qt.Key_Up:
            self.vchannel_incdec(1)
        elif e.key() == Qt.Qt.Key_Down:
            self.vchannel_incdec(-1)
        elif e.key() == Qt.Qt.Key_I:
            self.info_widget.setVisible(not self.info_widget.isVisible())
        elif e.key() in self.channel_keys:
            self.info_widget.input_add('.' if e.text() == '-' else e.text())
        elif e.key() in (Qt.Qt.Key_Enter, Qt.Qt.Key_Return, Qt.Qt.Key_Space):
            if self.last:
                self.parent.set_vchannel(self.last)
        elif e.key() == Qt.Qt.Key_G:
            self.clicked.emit()
        if e.key() == Qt.Qt.Key_T:
            current = self.master.player.video_get_spu()
            descs = self.master.player.video_get_spu_description()
            if not descs:
                return
            current_idx = 0
            for idx, id in enumerate(descs):
                if id[0] == current:
                    current_idx = idx
                    break
            current_idx += 1
            current_idx %= len(descs)
            new_spu = descs[current_idx]
            self.master.set_spu(new_spu[0])
            self.osd.display('%s (%d/%d)' % (new_spu[1], current_idx, len(descs) - 1))
        else:
            super(live, self).keyPressEvent(e)


