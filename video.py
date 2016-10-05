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

class video_proxy(Qt.QLabel):

    clicked = Qt.pyqtSignal()

    def __init__(self, parent, master):
        self.master = master
        super(video_proxy, self).__init__(parent)
        self.setAlignment(Qt.Qt.AlignCenter)
        self.setFocusPolicy(Qt.Qt.NoFocus)
        self.setMinimumWidth(1)
        self.setMinimumHeight(1)
        self.setSizePolicy(Qt.QSizePolicy.Minimum, Qt.QSizePolicy.Minimum)
        master.paint_proxy.connect(self.update)
        master.status_changed.connect(self.status)

    def status(self, message):
        if message:
             self.setText(message)
        else:
             self.clear()

    def resizeEvent(self, e):
        super(video_proxy, self).resizeEvent(e)
        if self.isVisible():
            self.master.resize(e.size())
        self.setStyleSheet('video_proxy { font-size: %dpx; }' % (self.height() / 15))

    def paintEvent(self, e):
        if not self.master.active:
            super(video_proxy, self).paintEvent(e)

    def moveEvent(self, e):
        super(video_proxy, self).moveEvent(e)
        if self.isVisible():
            self.master.move(e.pos())

    def showEvent(self, e):
        super(video_proxy, self).showEvent(e)
        if not e.spontaneous():
            self.master.clicked.connect(self.clicked)
            self.master.setGeometry(self.geometry())
            self.master.raise_()

    def hideEvent(self, e):
        super(video_proxy, self).hideEvent(e)
        if not e.spontaneous():
            self.master.clicked.disconnect(self.clicked)
            self.master.lower()

class video(Qt.QWidget):

    clicked = Qt.pyqtSignal()
    paint_proxy = Qt.pyqtSignal()
    status_changed = Qt.pyqtSignal(object)

    def __init__(self):
        self.active = False
        self.spu = None
        super(video, self).__init__()

    def status(self, message):
        self.status_changed.emit(message)

    def set_spu(self, spu):
        self.spu = spu

    def mouseReleaseEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, e):
        pass

    def video_live(self):
        self.active = True

    def video_restart(self):
        self.paint_proxy.emit()

    def video_dead(self):
        self.status(None)
        self.active = False
        self.paint_proxy.emit()
