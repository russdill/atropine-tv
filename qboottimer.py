#!/usr/bin/python

import clock_gettime
import math
from PyQt4 import Qt

def now():
    return clock_gettime.clock_gettime(clock_gettime.CLOCK_BOOTTIME)

class QBootTimer(Qt.QTimer):
    def __init__(self, parent=None):
        Qt.QAbstractEventDispatcher.instance().awake.connect(self.awake)
        self.expires = None
        self.real_interval = 0
        super(QBootTimer, self).__init__(parent)

    def timerEvent(self, e):
        self.update_expires(self.real_interval)
        super(QBootTimer, self).timerEvent(e)
        if self.real_interval != super(QBootTimer, self).interval():
            super(QBootTimer, self).setInterval(self.real_interval)

    def update_expires(self, msec):
        self.expires = now() + msec / 1000.0

    def setInterval(self, msec):
        self.update_expires(msec)
        self.real_interval = msec
        super(QBootTimer, self).setInterval(msec)

    def start(self, msec=None):
        if msec is not None:
            self.setInterval(msec)
        else:
            self.update_expires(self.real_interval)
        super(QBootTimer, self).start(self.real_interval)

    def awake(self):
        if self.expires is None or self.real_interval is None:
            return
        remaining = self.expires - now()
        if remaining < 0:
            remaining = 0
        super(QBootTimer, self).setInterval(math.ceil(remaining * 1000))
