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

from xml import sax

class channel_icons(sax.ContentHandler, sax.ErrorHandler):
    def __init__(self, filename='iconmap-LyngSat.xml'):
        self.context = 'root'
        self.contextStack = []
        self.contentList = []

        self.callsigns = dict()
        self.urls = dict()
        self.base_urls = dict()

        parser = sax.make_parser()
        parser.setContentHandler(self)
        parser.setErrorHandler(self)
        try:
            parser.parse(filename)
        except:
            pass

    def icon_url(self, callsign):
        callsign = callsign.lower()
        if callsign not in self.callsigns and callsign.endswith('hd'):
            callsign = callsign[:-2]
        network = self.callsigns[callsign]
        url = self.urls[network]
        baseurl, url = url.split(']')
        _, baseurl = baseurl.split('[')
        baseurl = self.base_urls[baseurl]
        return baseurl + url

    def startElement(self, name, attrs):
        """Callback run at the start of each XML element"""

        self.contextStack.append(self.context)
        self.contentList = []

        if self.context == 'root':
            self.context = name
            self.args = dict()

    def characters(self, ch):
        """Callback run whenever content is found outside of nodes"""

        self.contentList.append(ch)

    def endElement(self, name):
        """Callback run at the end of each XML element"""

        self.args[name] = content = ''.join(self.contentList)
        self.contentList = []

        if name == 'callsigntonetwork':
            self.callsigns[self.args['callsign'].lower()] = self.args['network']
        elif name == 'networktourl':
            self.urls[self.args['network']] = self.args['url']
        elif name == 'baseurl':
            self.base_urls[self.args['stub']] = self.args['url']

        self.context = self.contextStack.pop()

    def error(self, msg):
        """Callback run when a recoverable parsing error occurs"""
        raise Exception(msg)

    def fatalError(self, msg):
        """Callback run when a fatal parsing error occurs"""
        raise Exception(msg)

    def warning(self, msg):
        """Callback run when a parsing warning occurs"""
        pass
