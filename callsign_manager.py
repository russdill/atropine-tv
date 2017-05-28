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
import threading
import signal
import shutil
import pickle
import atomicwrites
import os.path
import logo_matcher

import datetime
import dateutil.tz

from urlparse import urljoin
import bs4

from PyQt4 import Qt

localtz = dateutil.tz.tzlocal()

class match_worker(Qt.QThread):
    done = Qt.pyqtSignal(object)

    def __init__(self, options):
        super(match_worker, self).__init__()
        self.matcher = logo_matcher.matcher(drop=options.channel_drop, resub=options.channel_resub)
        self.finished.connect(self.process_done)
        self.busy = False
        self.pending = False
        self.networks = dict()
        self.stations = dict()

    def start_networks(self, networks):
        # List of Lynq network names
        self.networks = networks
        self.pending = True
        self.process()

    def start_stations(self, stations):
        self.stations = stations
        self.pending = True
        self.process()

    def process(self):
        if self.pending and not self.busy:
            self.busy = True
            self.pending = False
            self.thread_networks = self.networks
            self.thread_stations = self.stations
            self.start(Qt.QThread.IdlePriority)

    def run(self):
        self.matcher.set_target_stations(self.thread_networks.keys())
        self.matcher.generate_mapping(self.thread_stations.keys())
        self.urls = dict()
        for station, network in self.matcher.mapping.iteritems():
            if network is not None:
                try:
                    network = self.thread_networks[network]
                    station = self.thread_stations[station]
                    self.urls[station] = network
                except:
                    pass

    def process_done(self):
        self.busy = False
        self.done.emit(self.urls)
        self.process()

class lyngsat_region(Qt.QNetworkAccessManager):
    updated = Qt.pyqtSignal()

    cache_period_sec = 20 * 24 * 60 * 60
    retry_delay_sec = 60 * 60

    def __init__(self, region, cache_dir):
        super(lyngsat_region, self).__init__()
        self.baseurl = 'https://www.lyngsat-logo.com/tvcountry/%s.html' % region
        self.cache_file = os.path.join(cache_dir, 'lyngsat-logo_%s.pickle' % region)
        self.finished.connect(self.xfer_finished)

        try:
            with open(self.cache_file, 'r') as f:
                self.networks = pickle.load(f)
            age = time.time() - os.path.getmtime(self.cache_file)
            delta = self.cache_period_sec - age
            if delta < 0:
                delta = 0

        except:
            self.networks = dict()
            delta = 0

        Qt.QTimer.singleShot(delta * 1000, self.retrieve_start)

    def retrieve_start(self):
        self.get(Qt.QNetworkRequest(Qt.QUrl(self.baseurl)))

    def xfer_finished(self, reply):
        reply.deleteLater()

        if reply.error() != Qt.QNetworkReply.NoError:
            # Retry in an hour
            Qt.QTimer.singleShot(retry_delay_sec * 1000, self.retrieve_start)
            return

        redirect = reply.attribute(Qt.QNetworkRequest.RedirectionTargetAttribute).toUrl()
        if not redirect.isEmpty():
            self.get(Qt.QNetworkRequest(redirect))
            return

        networks = dict()
        content_type = str(reply.rawHeader(Qt.QByteArray('Content-Type')))
        type_subtype, _, parameter = content_type.partition(';')
        charset = None
        if parameter:
            name, _, val = parameter.partition('=')
            name = name.strip()
            val = val.strip()
            if name == 'charset':
                charset = val

        page = bytearray(reply.readAll())
        try:
            page = page.decode(charset).encode('utf8')
        except:
            page = unicode(page)

        try:
            soup = bs4.BeautifulSoup(page, 'lxml')
            for td in soup.find_all('td'):
                a = td.find_all('a')
                if len(a) == 2:
                    try:
                        name = a[1].text.strip()
                        networks[name] = urljoin(self.baseurl, a[0].find_all('img')[0]['src']).strip()
                    except:
                        pass
        except:
            pass

        if networks:
            self.networks = networks
            try:
                with atomicwrites.atomic_write(self.cache_file, overwrite=True) as f:
                    pickle.dump(self.networks, f)
            except:
                pass

            self.updated.emit()

        Qt.QTimer.singleShot(self.cache_period_sec * 1000, self.retrieve_start)

class callsign_manager(Qt.QObject):
    updated = Qt.pyqtSignal()

    def __init__(self, parent, options):
        super(callsign_manager, self).__init__(parent)

        self.regions = []
        self.urls = dict()

        self.match = match_worker(options)
        self.match.done.connect(self.match_done)

        for region in options.channel_region:
            lr = lyngsat_region(region, options.icons)
            lr.updated.connect(self.region_updated)
            self.regions.append(lr)
        self.region_updated()

    def new_guide(self, guide_data):
        stations = dict()
        for id, station in guide_data.stations.iteritems():
            stations[station.name] = station.callSign
        self.match.start_stations(stations)

    def region_updated(self):
        networks = dict()
        for region in self.regions:
            networks.update(region.networks)
        self.match.start_networks(networks)

    def lookup_url(self, callsign):
        return self.urls[callsign]

    def match_done(self, urls):
        self.urls = urls
        self.updated.emit()

