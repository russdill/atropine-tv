from PyQt4 import Qt
import collections

# Font generated from http://www.fontsaddict.com
television_screen_with_antenna = """<?xml version="1.0" encoding="iso-8859-1"?>
<!-- Generator: Adobe Illustrator 16.0.4, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 width="55px" height="54.01px" viewBox="0 0 55 54.01" style="enable-background:new 0 0 55 54.01;" xml:space="preserve">
<g>
	<path id="path3378" style="fill:#040606;" d="M47.875,27.22c-2.503,0-4.538-2.032-4.538-4.536c0-2.506,2.035-4.536,4.538-4.536
		c2.508,0,4.536,2.03,4.536,4.536C52.411,25.188,50.383,27.22,47.875,27.22z M47.875,38.561c-2.503,0-4.538-2.03-4.538-4.537
		c0-2.505,2.035-4.537,4.538-4.537c2.508,0,4.536,2.032,4.536,4.537C52.411,36.53,50.383,38.561,47.875,38.561z M41.25,45.365
		c0,2.506-2.209,4.895-4.718,4.895H9.312C6.811,50.26,5,47.871,5,45.365V22.682c0-2.504,1.811-4.922,4.312-4.922h27.22
		c2.509,0,4.718,2.418,4.718,4.922V45.365z M50.142,14.01H33.33c-1.38,0-1.784-1.061-0.898-2.121l4.42-5.401
		c0.884-1.061,1.679-1.952,1.774-1.929c0.056,0.016,0.113,0.002,0.176,0.002c1.254,0,2.269-1.026,2.269-2.281
		c0-1.25-1.015-2.273-2.269-2.273c-1.25,0-2.269,1.015-2.269,2.265c0,0.135,0.016,0.264,0.044,0.39
		c0.046,0.214-0.602,1.236-1.486,2.296l-5.613,6.732c-0.883,1.061-1.786,1.92-2.015,1.92c-0.229,0-1.13-0.859-2.015-1.921
		l-5.61-6.731c-0.885-1.062-1.538-2.087-1.494-2.3c0.026-0.126,0.042-0.256,0.042-0.39c0-1.25-1.014-2.267-2.269-2.267
		c-1.25,0-2.269,1.017-2.269,2.267c0,1.255,1.019,2.269,2.269,2.269c0.065,0,0.123-0.012,0.18-0.026
		c0.097-0.023,0.893,0.817,1.777,1.879l4.417,5.501c0.884,1.061,0.481,2.121-0.898,2.121H4.776C2.274,14.01,0,15.64,0,18.145v31.757
		c0,2.508,2.274,4.108,4.776,4.108h45.366c2.509,0,4.858-1.601,4.858-4.108V18.145C55,15.64,52.651,14.01,50.142,14.01"/>
</g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g><g></g></svg>"""

cache = collections.OrderedDict()

def pixmap(sz):
    try:
        # Move to newest
        ret = cache.pop(sz)
        cache[sz] = ret
        return cache[sz]
    except:
        rend = Qt.QSvgRenderer(Qt.QByteArray(television_screen_with_antenna))
        img = Qt.QImage(sz * 0.9, Qt.QImage.Format_ARGB32)
        img.fill(0)
        painter = Qt.QPainter(img)
        rend.render(painter)
        painter.end()
        pm = Qt.QPixmap.fromImage(img)
        cache[sz] = pm
        if len(cache) > 20:
            # Delete oldest
            cache.popitem(last=False)
        return pm
