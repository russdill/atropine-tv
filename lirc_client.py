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

import pylirc
from PyQt4 import Qt

class client(Qt.QSocketNotifier):
    def __init__(self, dest, name, config):
        self.dest = dest
        sock = pylirc.init(name, config)
        pylirc.blocking(False)
        super(client, self).__init__(sock, Qt.QSocketNotifier.Read, dest)
        self.setEnabled(True)
        self.activated.connect(self.read_nextcode)

    def __del__(self):
        pylirc.exit()

    def read_nextcode(self):
        next = pylirc.nextcode()
        if next is None:
            return
        for s in next:
            releases = []
            for key in Qt.QKeySequence(s):

                mod = Qt.Qt.KeyboardModifiers(key & Qt.Qt.MODIFIER_MASK)
                key &= ~Qt.Qt.MODIFIER_MASK

                if mod:
                    text = QString('')
                else:
                    text = Qt.QKeySequence(key).toString();

                event = Qt.QKeyEvent(Qt.QEvent.KeyPress, key, mod, text=text)
                Qt.QCoreApplication.sendEvent(self.dest.focusWidget(), event)
                event = Qt.QKeyEvent(Qt.QEvent.KeyRelease, key, mod, text=text)
                releases.insert(0, event)

            for event in releases:
                Qt.QCoreApplication.sendEvent(self.dest.focusWidget(), event)
