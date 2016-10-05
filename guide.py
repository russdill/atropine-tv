#!/usr/bin/env python

from PyQt4 import Qt
import sys
import collections
import datetime
import dateutil.tz
import categories
import guide_data
import icon_manager
import video
import info
import effects

localtz = dateutil.tz.tzlocal()

class program_label(Qt.QLabel):

    nav = Qt.pyqtSignal(datetime.datetime, object)
    tune = Qt.pyqtSignal(str)
    prog_changed = Qt.pyqtSignal(tuple)

    @Qt.pyqtProperty(str)
    def category(self):
        return self._category

    def __init__(self, sched, time, end, vchannel, category):
        super(program_label, self).__init__()
        self._category = category if category else 'Unknown'
        if sched:
            title = sched.program.title
        else:
            title = 'No schedule info'
        self.first = False
        self.last = False
        self.sched = sched
        self.time = time
        self.end = end
        self.vchannel = vchannel
        self.setMinimumWidth(1)
        self.setFocusPolicy(Qt.Qt.StrongFocus)
        self.setAttribute(Qt.Qt.WA_ShowWithoutActivating);
        self.setText(title)

    def update_text(self):
        cr = self.contentsRect()
        cr.adjust(self.margin(), self.margin(), -self.margin(), -self.margin())
        m = Qt.QFontMetrics(self.font())
        text = m.elidedText(self.orig_text, Qt.Qt.ElideRight, cr.width())
        super(program_label, self).setText(text)

    def setText(self, text):
        self.orig_text = text
        self.update_text()

    def resizeEvent(self, e):
        self.update_text()
        super(program_label, self).resizeEvent(e)

    def focusInEvent(self, e):
        super(program_label, self).focusInEvent(e)
        self.prog_changed.emit((self.time, self.sched))
        self.nav.emit(self.time, self.vchannel)

    def mouseDoubleClickEvent(self, me):
        self.tune.emit(self.vchannel)

    def keyPressEvent(self, e):
        if e.key() == Qt.Qt.Key_Right and not self.last:
            self.focusNextChild()
        elif e.key() == Qt.Qt.Key_Left and not self.first:
            self.focusPreviousChild()
        elif e.key() in (Qt.Qt.Key_Enter, Qt.Qt.Key_Return, Qt.Qt.Key_Space):
            if self.vchannel:
                self.tune.emit(self.vchannel)
        else:
            super(program_label, self).keyPressEvent(e)

class schedule_row_widget(Qt.QHBoxLayout):

    nav = Qt.pyqtSignal(datetime.datetime, object)
    tune = Qt.pyqtSignal(str)
    prog_changed = Qt.pyqtSignal(tuple)

    def __init__(self, vchannels, delta, duration, master=False):
        self.vchannels = vchannels
        self.widgets = []
        self.selected_time = None
        self.master = master
        self.delta = delta
        self.duration = duration
        self.vchannel = None
        self.start_time = None
        self.end_time = None
        self.selected = None

        super(schedule_row_widget, self).__init__()

        self.setSpacing(0)

    def set_vchannel(self, vchannel):
        if self.delta:
            try:
                idx = self.vchannels.keys().index(vchannel)
                idx = (idx + self.delta) % len(self.vchannels)
                vchannel = self.vchannels.keys()[idx]
            except:
                vchannel = None
        else:
            vchannel = unicode(vchannel)
        if vchannel == self.vchannel:
            return
        self.vchannel = vchannel
        self.update_row()

    def set_start_time(self, time):
        self.start_time = time
        self.end_time = self.start_time + self.duration
        self.update_row()

    def set_selected_time(self, time):
        self.selected_time = time
        if self.master:
            self.do_highlight()

    def do_nav(self, time, vchannel):
        w = self.parentWidget().focusWidget()
        if self.selected_time >= w.time and self.selected_time < w.end:
            time = self.selected_time
        self.nav.emit(time, vchannel)

    def do_highlight(self):
        to_select = self.widgets[0] if self.widgets else None
        for w in self.widgets:
            if w.time > self.selected_time:
                break
            to_select = w
        if to_select:
            to_select.show()
            to_select.setFocus()

    def update_row(self):
        old_widgets = self.widgets
        for w in old_widgets:
            self.removeWidget(w)
            w.deleteLater()
        self.widgets = []

        if not self.start_time:
            return

        try:
            sched = self.vchannels[self.vchannel].station.schedule.entries
        except:
            sched = dict()
        last_time = self.start_time
        last_min = 0
        total_min = (self.end_time - self.start_time).total_seconds() / 60
        last_widget = None

        def add(entry, time, end, category, min):
            curr = program_label(entry, time, end, self.vchannel, category)
            curr.tune.connect(self.tune)
            curr.nav.connect(self.do_nav)
            curr.prog_changed.connect(self.prog_changed)
            self.widgets.append(curr)
            self.addWidget(curr, min)
            return idx

        idx = 0
        for time, entry in sched.iteritems():
            duration = datetime.timedelta(minutes=entry.duration)
            start = time
            end = time + duration
            actual_end = end

            if end <= self.start_time:
                continue

            if start >= self.end_time:
                break

            start = max(start, self.start_time)
            end = min(end, self.end_time)
            min_start = (start - self.start_time).total_seconds() / 60
            min_span = (end - start).total_seconds() / 60
            min_end = min_start + min_span

            min_slack = min_start - last_min
            if min_slack < 1:
                pass
            if min_slack < 5:
                # Small missing program data, fudge together
                if last_widget:
                    self.setStretch(last_widget, self.stretch(last_widget) + min_slack / 2)
                    last_min += min_slack / 2
                    min_slack -= min_slack / 2
                min_span += min_start - last_min
                min_start = last_min
            else:
                # Large missing region, create Missing program data entry
                last_widget = add(None, last_time, start, None, min_slack)
                last_time = start
                last_min = min_start
                idx += 1

            if not min_span:
                continue

            try:
                genre = entry.program.genre[0]
            except:
                genre = None
            last_widget = add(entry, time, actual_end, genre, min_span)
            last_time = end
            last_min = min_end
            idx += 1

        min_slack = total_min - last_min
        if min_slack > 5:
            add(None, last_time, self.end_time, None, min_slack)

        self.widgets[0].first = True
        self.widgets[-1].last = True
        if self.master and self.selected_time:
            self.do_highlight()

class guide_header_widget(Qt.QLabel):
    def __init__(self):
        super(guide_header_widget, self).__init__()
        self.setAlignment(Qt.Qt.AlignCenter)
        self.setFocusPolicy(Qt.Qt.NoFocus)

    def set_selected_time(self, time):
        self.setText('<small>' + time.strftime('%A %B ') + str(time.day) + time.strftime(', %Y') + '</small>')

class time_header_widget(Qt.QLabel):
    def __init__(self, delta):
        super(time_header_widget, self).__init__()
        self.delta = delta

    def set_start_time(self, time):
        time = time + self.delta
        self.setText('<small>' + time.strftime("%l:%M %p").strip() + '</small>')

class guide_widget(Qt.QWidget):

    vchannel_changed = Qt.pyqtSignal(object)
    selected_time_changed = Qt.pyqtSignal(datetime.datetime)
    start_time_changed = Qt.pyqtSignal(datetime.datetime)

    done = Qt.pyqtSignal()

    def __init__(self, parent, options=None, video_widget=None, icon_manager=None, vchannels=None):
        super(guide_widget, self).__init__(parent)
        self.parent = parent
        self.vchannels = vchannels
        self.vchannel = None
        self.n_epg_rows = options.guide_rows
        self.n_epg_cols = options.guide_cols
        self.active_row = 2
        self.start_time = None

        grid = Qt.QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        row = 0
        col = 0

        self.proxy = video.video_proxy(self, video_widget)
        self.proxy.clicked.connect(self.done)
        grid.addWidget(self.proxy, row, col, 4, 2)
        grid.setColumnStretch(col, 10)
        grid.setColumnStretch(col+1, 12)
        col += 2

        header = guide_header_widget()
        self.selected_time_changed.connect(header.set_selected_time)
        grid.addWidget(header, row, col, 1, self.n_epg_cols)
        grid.setRowStretch(row, 1)
        row += 1

        now_label = info.now_widget()
        grid.addWidget(now_label, row, col, 1, self.n_epg_cols)
        row += 1

        delta = datetime.timedelta(minutes=30)
        curr = datetime.timedelta(0)
        for i in range(0, self.n_epg_cols):
            label = time_header_widget(curr)
            self.start_time_changed.connect(label.set_start_time)
            grid.addWidget(label, row, i + col)
            grid.setColumnStretch(i + col, 20)
            curr = curr + delta
        row += 1

        info_widget = info.program_info_widget(self, 'guide')

        duration = datetime.timedelta(minutes=30) * self.n_epg_cols
        large_station_info = info.station_info_guide_large(self, icon_manager, vchannels, 0)
        info_widget.stackUnder(large_station_info)
        self.vchannel_changed.connect(large_station_info.set_vchannel)

        self.channel_input = info.vchannel_input(self, vchannels)
        self.channel_input.set_station_info(large_station_info)
        self.channel_input.done.connect(self.set_vchannel)

        for i in range(0, self.n_epg_rows):
            w = schedule_row_widget(vchannels, i - self.active_row, duration, i == self.active_row)

            w.prog_changed.connect(info_widget.set_program)
            w.nav.connect(self.do_nav)
            w.tune.connect(self.parent.set_vchannel)

            self.vchannel_changed.connect(w.set_vchannel)
            self.start_time_changed.connect(w.set_start_time)
            self.selected_time_changed.connect(w.set_selected_time)

            grid.addLayout(w, row, col, 1, self.n_epg_cols)
            grid.setRowStretch(row, 2)

            if i == self.active_row:
                self.master_row = w
                grid.addWidget(info_widget, row+1, col, 3, self.n_epg_cols)

                grid.addWidget(large_station_info, row, 0, 4, 2)

                grid.setRowStretch(row+1, 2)
                grid.setRowStretch(row+2, 2)
                grid.setRowStretch(row+3, 2)

                row += 4
            else:
                station_info = info.station_info_guide_small(self, icon_manager, vchannels, i - self.active_row)
                self.vchannel_changed.connect(station_info.set_vchannel)
                if i != 0:
                    # First row is not visible
                    grid.addWidget(station_info.icon, row, 0)
                    grid.addWidget(station_info.info, row, 1)
                    station_info.icon.stackUnder(large_station_info)
                    station_info.info.stackUnder(large_station_info)
                row += 1

    def showEvent(self, e):
        super(guide_widget, self).showEvent(e)
        if not e.spontaneous():
            self.channel_input.cancel()

            self.start_time = None
            self.set_selected_time(datetime.datetime.now(localtz))
            self.vchannel_changed.emit(self.parent.vchannel)

    def hideEvent(self, e):
        super(guide_widget, self).hideEvent(e)
        if not e.spontaneous():
            self.channel_input.cancel()

    def set_vchannel(self, vchannel):
        if vchannel not in self.vchannels.keys():
            if self.vchannels:
                vchannel = self.vchannels.keys()[0]
        self.vchannel = vchannel
        self.vchannel_changed.emit(self.vchannel)

    def vchannel_incdec(self, incdec):
        try:
            idx = self.vchannels.keys().index(self.vchannel) + incdec
            idx %= len(self.vchannels)
            self.set_vchannel(self.vchannels.keys()[idx])
        except:
            if self.vchannels:
                self.set_vchannel(self.vchannels.keys()[0])

    def set_start_time(self, time):
        time = time + datetime.timedelta(seconds=59)
        minute = 0 if time.minute < 30 else 30
        time = time.replace(minute=minute,second=0,microsecond=0)
        self.start_time = time
        self.end_time = time + datetime.timedelta(minutes=30) * self.n_epg_cols
        self.start_time_changed.emit(time)

    def set_selected_time(self, time):
        self.selected_time = time
        if not self.start_time:
             self.set_start_time(time)
        self.selected_time_changed.emit(time)

    channel_keys = [
        Qt.Qt.Key_0,
        Qt.Qt.Key_1,
        Qt.Qt.Key_2,
        Qt.Qt.Key_3,
        Qt.Qt.Key_4,
        Qt.Qt.Key_5,
        Qt.Qt.Key_6,
        Qt.Qt.Key_7,
        Qt.Qt.Key_8,
        Qt.Qt.Key_9,
        Qt.Qt.Key_Period,
        Qt.Qt.Key_Underscore
    ]

    def keyPressEvent(self, e):
        if e.key() == Qt.Qt.Key_Up:
            self.vchannel_incdec(-1)
        elif e.key() == Qt.Qt.Key_Down:
            self.vchannel_incdec(1)
        elif e.key() == Qt.Qt.Key_PageUp:
            self.vchannel_incdec(-(self.n_epg_rows - 1))
        elif e.key() == Qt.Qt.Key_PageDown:
            self.vchannel_incdec(self.n_epg_rows - 1)
        elif e.key() == Qt.Qt.Key_Home:
            self.start_time = None
            self.set_selected_time(datetime.datetime.now(localtz))
        elif e.key() == Qt.Qt.Key_Right:
            self.set_start_time(self.end_time)
        elif e.key() == Qt.Qt.Key_Left:
            time = self.start_time - self.n_epg_rows * datetime.timedelta(minutes=30)
            self.set_start_time(time)
        elif e.key() == Qt.Qt.Key_Escape:
            self.done.emit()
        elif e.key() in self.channel_keys:
            self.channel_input.input_add('.' if e.text() == '-' else e.text())
        else:
            super(guide_widget, self).keyPressEvent(e)

    def wheelEvent(self, e):
        if e.orientation() == Qt.Qt.Horizontal:
            if e.delta() > 0:
                time = self.start_time - self.n_epg_rows * datetime.timedelta(minutes=30)
                self.set_start_time(time)
            else:
                self.set_start_time(self.end_time)
        else:
            self.vchannel_incdec(-e.delta() / 120)

    def do_nav(self, time, vchannel):
        changed = vchannel != self.vchannel
        if changed and (vchannel != None) and len(vchannel):
            self.set_vchannel(vchannel)
        self.set_selected_time(time.replace(tzinfo=localtz))

    def new_guide(self):
        self.set_vchannel(self.vchannel)
