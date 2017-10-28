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
import x11_colors

class category_colors(sax.ContentHandler, sax.ErrorHandler, dict):
    def __init__(self, filename='categories.xml'):
        parser = sax.make_parser()
        parser.setContentHandler(self)
        parser.setErrorHandler(self)
        parser.parse(filename)

    def startElement(self, name, attrs):
        if name == 'catcolor':
            self[attrs.get('category')] = x11_colors.map(attrs.get('color'))

    def characters(self, ch):
        pass

    def endElement(self, name):
        pass

    def error(self, msg):
        """Callback run when a recoverable parsing error occurs"""
        raise Exception(msg)

    def fatalError(self, msg):
        """Callback run when a fatal parsing error occurs"""
        raise Exception(msg)

    def warning(self, msg):
        """Callback run when a parsing warning occurs"""
        pass

