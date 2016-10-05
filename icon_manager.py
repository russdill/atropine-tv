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
from PyQt4 import Qt

class icon_manager(Qt.QNetworkAccessManager):
    def __init__(self, options):
        super(icon_manager, self).__init__()
        self.iconmap = icons.channel_icons(options.iconmap)
        self.finished.connect(self.xfer_finished)
        self.path = options.icons

        self.queue = []
        self.cache = dict()
        self.callsigns = dict()
        self.labels = dict()
        self.running = None
        self.failed = dict()

    def request(self, callsign, label):
        try:
            label.setPixmap(self.cache[callsign])
        except:
            pass
        try:
            url = self.iconmap.icon_url(callsign)
        except:
            return
        basename = os.path.basename(url)
        path = os.path.join(self.path, basename);

        pixmap = Qt.QPixmap()
        if pixmap.load(path):
            label.setPixmap(pixmap)
            self.cache[callsign] = pixmap
            # Check if we should try for a newer one (every 6 weeks)
            if time.time() - os.path.getmtime(path) < 60 * 60 * 24 * 7 * 6:
                return

        # LyngSat hack
        hires = url.replace('logo/tv', 'hires')

        self.enqueue(callsign, [Qt.QUrl(hires), Qt.QUrl(url)], label)

    def enqueue(self, callsign, url, label):
        if callsign in self.failed:
            # Retry after 30 minutes
            if (datetime.datetime.now() - self.failed[callsign]).total_seconds() > 60 * 30:
                del self.failed[callsign]
            else:
                return

        self.callsigns[callsign] = (url, label)
        if label is not None:
            self.labels[label] = callsign

        if callsign == self.running:
            return

        # Move to head
        if callsign in self.queue:
            self.queue.remove(callsign)
        self.queue.insert(0, callsign)

        self.dequeue()

    def dequeue(self):
        if self.running or not len(self.queue):
            return

        callsign = self.queue.pop()
        self.running = callsign
        self.remaining_urls = self.callsigns[callsign][0][1:]

        self.get(Qt.QNetworkRequest(self.callsigns[callsign][0][0]))

    def forget_label(self, label):
        try:
            callsign = self.labels.pop(label)
            url, label = self.callsigns[callsign]
        except:
            return
        self.callsigns[callsign] = (url, None)

    def forget_labels(self):
        for label, callsign in self.labels.iteritems():
            url, label = self.callsigns[callsign]
            self.callsigns[callsign] = (url, None)
        self.labels = dict()

    def xfer_finished(self, reply):

        reply.deleteLater()
        callsign = self.running

        if reply.error() != Qt.QNetworkReply.NoError:
            if len(self.remaining_urls):
                self.get(Qt.QNetworkRequest(self.remaining_urls[0]))
                del self.remaining_urls[0]
                return

            self.failed[callsign] = datetime.datetime.now()
            url, label = self.callsigns.pop(callsign)
            if label is not None:
                del self.labels[label]
            self.running = None

            # Wait a bit between retries
            Qt.QTimer.singleShot(1000, self.dequeue())
            self.dequeue()
            return

        redirect = reply.attribute(Qt.QNetworkRequest.RedirectionTargetAttribute).toUrl()
        if not redirect.isEmpty():
            self.get(Qt.QNetworkRequest(redirect))

        callsign = self.running
        url, label = self.callsigns.pop(callsign)
        if label is not None:
            del self.labels[label]
        self.running = None

        basename = os.path.basename(str(url[0].toString()))
        path = os.path.join(self.path, basename)
        file = Qt.QFile(path)
        file.open(Qt.QIODevice.WriteOnly)
        file.write(reply.readAll())
        file.close()

        if label is not None:
            pixmap = Qt.QPixmap()
            if pixmap.load(path):
                label.setPixmap(pixmap)
                self.cache[callsign] = pixmap
            else:
                os.remove(path)
                self.failed[callsign] = datetime.datetime.now()

        reply.deleteLater()
        self.dequeue()
