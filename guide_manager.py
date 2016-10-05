import guide_data

import sys
import pyschedules.retrieve
import threading
import signal
import shutil
import StringIO

import datetime
import dateutil.tz

from PyQt4 import Qt

localtz = dateutil.tz.tzlocal()

class parse_worker(Qt.QThread):
    done = Qt.pyqtSignal(guide_data.guide_data)
    failed = Qt.pyqtSignal()

    def __init__(self, filename):
        super(parse_worker, self).__init__()
        self.filename = filename

    def start(self, fileobj, initial=False):
        self.fobj = fileobj
        self.initial = initial
        super(parse_worker, self).start()

    def run(self):
        try:
            tmp = StringIO.StringIO()
            shutil.copyfileobj(self.fobj, tmp)
            tmp.seek(0)
            d = guide_data.guide_data(tmp)
            self.done.emit(d)
            if not self.initial:
                tmp.seek(0)
                try:
                    with open(self.filename, 'w') as out:
                        shutil.copyfileobj(tmp, out)
                except:
                    pass
        except:
            self.failed.emit()
        finally:
            del self.fobj

class retrieve_worker(Qt.QThread):
    done = Qt.pyqtSignal(object)
    failed = Qt.pyqtSignal()

    def __init__(self, login, duration):
        super(retrieve_worker, self).__init__()
        self.login = login
        self.duration = duration

    def run(self):
        try:
            utc_start = datetime.datetime.utcnow()
            utc_stop = utc_start + self.duration
            u, p = self.login
            f = pyschedules.retrieve.get_file_object(u, p, utc_start, utc_stop)
            self.done.emit(f)
        except:
            self.failed.emit()

class guide_manager(Qt.QObject):
    new_guide = Qt.pyqtSignal(guide_data.guide_data)

    def __init__(self, parent, options=None):
        super(guide_manager, self).__init__(parent)
        self.first = True

        self.minimum_sched = datetime.timedelta(hours=8)
        self.minimum_fresh = datetime.timedelta(days=1)
        fetch_duration = datetime.timedelta(days=1)

        self.filename = options.sched
        self.parse = parse_worker(self.filename)
        self.retrieve = retrieve_worker((options.username, options.password), fetch_duration)

        self.parse.done.connect(self.parse_done)
        self.parse.done.connect(self.new_guide)
        self.parse.failed.connect(self.parse_failed)
        self.retrieve.done.connect(self.parse.start)
        self.retrieve.failed.connect(self.retrieve_failed)

        self.timer = Qt.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.retrieve.start)

        Qt.QTimer.singleShot(0, self.parse_first)

    def retrieve_failed(self):
        # Wait 5 minutes and try again
        self.timer.start(5 * 60 * 1000)

    def parse_first(self):
        try:
            self.parse.start(open(self.filename, 'r'), True)
        except:
            self.parse_failed()

    def parse_done(self, f):
        now = datetime.datetime.now(localtz)

        # We need at least minimum_sched time of schedule data from now till validTo
        update_time = f.validTo - self.minimum_sched
        minimum_sched_wait = update_time - now

        # Schedule data should have been fetched in the past minimum_fresh time
        update_time = f.validFrom + self.minimum_fresh
        fresh_wait = update_time - now

        wait = min(minimum_sched_wait, fresh_wait)
        if wait.total_seconds() < 0:
            self.retrieve.start()
        else:
            self.timer.start(wait.total_seconds() * 1000)

    def parse_failed(self):
        if self.first:
            self.first = False
            self.retrieve.start()
        else:
            # Wait 5 minutes and try again
            self.timer.start(5 * 60 * 1000)
