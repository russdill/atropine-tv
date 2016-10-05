from xml import sax
import webcolors

class category_colors(sax.ContentHandler, sax.ErrorHandler, dict):
    def __init__(self, filename='categories.xml'):
        parser = sax.make_parser()
        parser.setContentHandler(self)
        parser.setErrorHandler(self)
        parser.parse(filename)

    def startElement(self, name, attrs):
        if name == 'catcolor':
            self[attrs.get('category')] = webcolors.html5_parse_legacy_color(attrs.get('color'))

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

