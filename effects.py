from PyQt4 import Qt
import ctypes
import sip

_qtgui = ctypes.CDLL("libQtGui.so")
_qt_blurImage = _qtgui._Z12qt_blurImageP8QPainterR6QImagedbbi

def qt_blurImage(p, blurImage, radius, quality, alphaOnly, transposed=0):
    p = ctypes.c_void_p(sip.unwrapinstance(p))
    blurImage = ctypes.c_void_p(sip.unwrapinstance(blurImage))
    radius = ctypes.c_double(radius)
    quality = ctypes.c_bool(quality)
    alphaOnly = ctypes.c_bool(alphaOnly)
    transposed = ctypes.c_int(transposed)
    _qt_blurImage(p, blurImage, radius, quality, alphaOnly, transposed)

class QGraphicsBlurShadowEffect(Qt.QGraphicsEffect):
    def __init__(self, *args, **kwargs):
        super(QGraphicsBlurShadowEffect, self).__init__(*args, **kwargs)
        self._distance = 4.0
        self._blurRadius = 10.0
        self._color = Qt.QColor(0, 0, 0, 80)

    @Qt.pyqtProperty(float)
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, value):
        self._distance = value

    @Qt.pyqtProperty(float)
    def blurRadius(self):
        return self._blurRadius

    @blurRadius.setter
    def blurRadius(self, value):
        self._blurRadius = value

    @Qt.pyqtProperty(Qt.QColor)
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    def draw(self, painter):
        # if nothing to show outside the item, just draw source
        if (self.blurRadius + self.distance) <= 0:
            drawSource(painter)
            return

        mode = Qt.QGraphicsEffect.PadToEffectiveBoundingRect
        px, offset = self.sourcePixmap(Qt.Qt.DeviceCoordinates, mode)

        # return if no source
        if px.isNull():
            return

        # save world transform
        restoreTransform = painter.worldTransform()
        painter.setWorldTransform(Qt.QTransform())

        # Calculate size for the background image
        szi = Qt.QSize(px.size().width() + 2 * self.distance, px.size().height() + 2 * self.distance)

        tmp = Qt.QImage(szi, Qt.QImage.Format_ARGB32_Premultiplied)
        scaled = Qt.QPixmap(px.scaled(szi))
        tmp.fill(0)

        tmpPainter = Qt.QPainter(tmp)
        tmpPainter.setCompositionMode(Qt.QPainter.CompositionMode_Source)
        tmpPainter.drawPixmap(Qt.QPointF(-self.distance, -self.distance), scaled)
        tmpPainter.end()

        # blur the alpha channel
        blurred = Qt.QImage(tmp.size(), Qt.QImage.Format_ARGB32_Premultiplied)
        blurred.fill(0)
        blurPainter = Qt.QPainter(blurred)
        qt_blurImage(blurPainter, tmp, self.blurRadius, False, True)
        blurPainter.end()

        tmp = blurred

        # blacken the image...
        tmpPainter.begin(tmp)
        tmpPainter.setCompositionMode(Qt.QPainter.CompositionMode_SourceIn)
        tmpPainter.fillRect(tmp.rect(), self.color)
        tmpPainter.end()

        # draw the blurred shadow...
        painter.drawImage(offset, tmp)

        # draw the actual pixmap...
        painter.drawPixmap(offset, px, Qt.QRectF())

        # restore world transform
        painter.setWorldTransform(restoreTransform)

    def boundingRectFor(self, rect):
        delta = self.blurRadius + self.distance
        return rect.united(rect.adjusted(-delta, -delta, delta, delta))


