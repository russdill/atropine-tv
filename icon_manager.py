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

import icons
import datetime
import os
import sys
import time
import atomicwrites

from PyQt4 import Qt

class callsign(Qt.QObject):
    no_url = 0
    idle = 1
    waiting = 2
    ready = 3

    url_hires = 0
    url_sd = 1
    url_none = 2

    def __init__(self, callsign_name, callsign_manager, icon_manager):
        super(callsign, self).__init__()
        self.callsign = callsign_name
        self.labels = []
        self.url = None
        self.state = self.no_url
        self.url_state = self.url_none
        self.icon_name = None
        self.retry_timer = Qt.QTimer()
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self.retry)
        self.use_cache = True
        self.pixmap = None

        self.cm = callsign_manager
        self.im = icon_manager
        self.cm.updated.connect(self.cm_updated)
        self.cm_updated()

    def cm_updated(self):
        url = None
        try:
            url = self.cm.lookup_url(self.callsign)
        except Exception as e:
            url = None

        if url is None:
            self.url = None
            self.icon_name = None
            self.state = self.no_url
            self.pixmap = None
            for label in self.labels:
                label.clear()
            self.im.cancel(self)
        elif self.url != url:
            self.url = url;
            self.icon_name = os.path.basename(url)
            self.state = self.waiting
            self.url_state = self.url_hires
            self.use_cache = True
            self.im.enqueue(self)
        else:
            return

    def next_url(self):
        if self.url_state == self.url_hires:
            self.url_state = self.url_sd
            return self.url.replace('logo/tv', 'hires')
        elif self.url_state == self.url_sd:
            self.url_state = self.url_none
            return self.url
        return None

    def add_label(self, label):
        self.labels.append(label)
        self.im.prioritize(self)
        if self.pixmap is None:
            label.clear()
        else:
            label.setPixmap(self.pixmap)

    def retry(self):
        if self.state == self.ready:
            self.url_state = self.url_hires
            self.state = self.waiting
            self.im.enqueue(self)

    def loaded(self, pixmap, age):
        if pixmap is None:
            # Retry in 30 minutes
            delta = 30 * 60
        else:
            self.pixmap = pixmap
            for label in self.labels:
                label.setPixmap(self.pixmap)

            # Try to get a new copy every 20 days
            self.use_cache = False
            delta = 60 * 60 * 24 * 20 - age
            if delta < 0:
                delta = 0;

        self.retry_timer.start(delta * 1000)
        self.state = self.ready

    def del_label(self, label):
        self.labels.remove(label)

class icon_manager(Qt.QNetworkAccessManager):
    def __init__(self, callsign_manager, options):
        super(icon_manager, self).__init__()
        self.cm = callsign_manager
        self.finished.connect(self.xfer_finished)
        self.path = options.icons

        self.queue = []
        self.callsigns = dict()
        self.labels = dict()
        self.running = None

    def enqueue(self, callsign):
        if callsign != self.running:
            self.queue.insert(0, callsign)
        self.dequeue()

    def prioritize(self, callsign):
        if callsign in self.queue:
            self.queue.remove(callsign)
            self.queue.insert(0, callsign)

    def cancel(self, callsign):
        if callsign in self.queue:
            self.queue.remove(callsign)
        if callsign == self.running:
            self.running = None

    def forget_label(self, label):
        if label in self.labels:
            self.labels[label].del_label(label)
            del self.labels[label]

    def request(self, callsign_name, label):
        self.forget_label(label)

        if callsign_name in self.callsigns:
            cs = self.callsigns[callsign_name]
        else:
            cs = callsign(callsign_name, self.cm, self)
            self.callsigns[callsign_name] = cs

        self.labels[label] = cs
        cs.add_label(label)

    def dequeue(self):
        if self.running or not len(self.queue):
            return

        self.running = self.queue.pop()
        if self.running.use_cache:
            self.process()
        else:
            self.download()

    def process(self):
        path = os.path.join(self.path, self.running.icon_name)

        pixmap = Qt.QPixmap()
        if pixmap.load(path):
            # Done with request, success
            age = time.time() - os.path.getmtime(path)
            self.running.loaded(pixmap, age)
            self.running = None

            # Don't recurse
            Qt.QTimer.singleShot(0, self.dequeue)
        else:
            self.download()

    def download(self):
        url = self.running.next_url()
        if url is not None:
            url = Qt.QUrl(url)
            self.get(Qt.QNetworkRequest(url))
        else:
            # Done with request, failed
            self.running.loaded(None, None)
            self.running = None

            # Wait a bit between retries
            Qt.QTimer.singleShot(1000, self.dequeue)

    def xfer_finished(self, reply):
        reply.deleteLater()

        if self.running is None:
            self.dequeue()
            return

        if reply.error() != Qt.QNetworkReply.NoError:
            self.download()
            return

        redirect = reply.attribute(Qt.QNetworkRequest.RedirectionTargetAttribute).toUrl()
        if not redirect.isEmpty():
            self.get(Qt.QNetworkRequest(redirect))
            return

        basename = os.path.basename(self.running.icon_name)
        path = os.path.join(self.path, basename)
        with atomicwrites.atomic_write(path, overwrite=True) as f:
            f.write(reply.readAll())

        # Will load pixmap or get next url if file is corrupted
        self.process()
