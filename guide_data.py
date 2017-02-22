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
import pyschedules.retrieve
import collections
import datetime
import dateutil.tz

# wget http://services.mythtv.org/channel-icon/master-iconmap

localtz = dateutil.tz.tzlocal()

def sanitize_datetime(time):
    if time is None:
        return None
    return time.pydatetime().replace(tzinfo=dateutil.tz.tzutc()).astimezone(localtz)

class Station(object):
    def __init__(self, callSign, name, affiliate, fccChannelNumber):
        self.callSign = callSign
        self.name = name
        self.affiliate = affiliate
        self.fccChannelNumber = fccChannelNumber

class Lineup(object):
    def __init__(self, name, location, device, _type, postalCode):
        self.name = name
        self.location = location
        self.device = device
        self._type = _type
        self.postalCode = postalCode

class Mapping_Station(object):
    def __init__(self, lineup, station, channel, validFrom, validTo, onAirFrom, onAirTo):
        self.station = station
        self.channel = channel
        self.lineup = lineup
        self.validFrom = sanitize_datetime(validFrom) # FIXME: Handle changeover
        self.validTo = sanitize_datetime(validTo)
        self.onAirFrom = sanitize_datetime(onAirFrom)
        self.onAirTo = sanitize_datetime(onAirTo)

class Mapping(object):
    def __init__(self):
        self.stations = dict()
        self.channels = dict()
        self.all = []

    def finalize(self):
        self.channels = collections.OrderedDict(sorted(self.channels.iteritems(), key=lambda x: float(x[0])))
        del self.all

    def add(self, lineup, station, channel, channelMinor, validFrom, validTo, onAirFrom, onAirTo):
        if channelMinor is not None:
            channel += '.' + channelMinor
        st = Mapping_Station(lineup, station, channel, validFrom, validTo, onAirFrom, onAirTo)
        self.stations[station] = st
        self.channels[channel] = st
        self.all.append(st)

class Schedule_Station(object):
    def __init__(self):
        self.entries = dict()

    def finalize(self):
        self.entries = collections.OrderedDict(sorted(self.entries.iteritems(), key=lambda x: x[0]))

    def add(self, program, time, duration, new, stereo, subtitled, hdtv, closeCaptioned, ei, tvRating, dolby, partNumber, partTotal):
        time = sanitize_datetime(time)
        self.entries[time] = Schedule_Entry(program, duration, new, stereo, subtitled, hdtv, closeCaptioned, ei, tvRating, dolby, partNumber, partTotal)

class Schedule_Entry(object):
    def __init__(self, program, duration, new, stereo, subtitled, hdtv, closeCaptioned, ei, tvRating, dolby, partNumber, partTotal):
        self.program = program
        self.duration = duration
        self.new = new
        self.stereo = stereo
        self.subtitled = subtitled
        self.hdtv = hdtv
        self.closeCaptioned = closeCaptioned
        self.ei = ei
        self.tvRating = tvRating
        self.dolby = dolby
        self.partNumber = partNumber
        self.partTotal = partTotal

class Program(object):
    def __init__(self, series, title, subtitle, description, mpaaRating, starRating, runTime, year, showType, colorCode, originalAirDate, syndicatedEpisodeNumber, advisories):
        self.series = series
        self.title = title
        self.subtitle = subtitle
        self.description = description
        self.mpaaRating = mpaaRating
        self.starRating = starRating
        self.runTime = runTime
        self.year = year
        self.showType = showType
        self.colorCode = colorCode
        self.originalAirDate = originalAirDate
        self.syndicatedEpisodeNumber = syndicatedEpisodeNumber
        self.advisories = advisories
        self.genre = None
        self.crew = []

class Crew_Member(object):
    def __init__(self, role, fullname, givenname, surname):
        self.role = role
        self.fullname = fullname if fullname else ' '.join(givenname, surname)
        self.givenname = givenname
        self.surname = surname

class Genre(list):
    def __init__(self, genre, relevance):
        self.append((genre, relevance))

    def add(genre, relevance):
        self.append((genre, relevance))

class guide_data(pyschedules.interfaces.ientity_trigger.IEntityTrigger, pyschedules.interfaces.iprogress_trigger.IProgressTrigger):
    def __init__(self, filename='sched.xml'):
        self.stations = dict()
        self.lineups = dict()
        self.programs = dict()
        self.genres = dict()
        self.schedules = dict()
        self.mappings = dict()
        self.crews = dict()
        pyschedules.retrieve.process_file_object(filename, self, self)
        self.finalize()

    def finalize(self):
        self.channels = list()
        for l in self.mappings.itervalues():
            for i in l.all:
                i.station = self.stations[i.station]
            l.finalize()
        for s in self.schedules.itervalues():
            s.finalize()
            for e in s.entries.itervalues():
                e.program = self.programs[e.program]
        for id, s in self.stations.iteritems():
            s.schedule = self.schedules[id]
        for prog, genre in self.genres.iteritems():
            genre = [x[0] for x in sorted(genre, key=lambda x: x[1])]
            self.genres[prog] = genre
            self.programs[prog].genre = genre
        for prog, crew in self.crews.iteritems():
            self.programs[prog].crew = crew

    def new_station(self, _id, callSign, name, affiliate, fccChannelNumber):
        self.stations[_id] = Station(callSign, name, affiliate, fccChannelNumber)

    def new_lineup(self, name, location, device, _type, postalCode, _id):
        self.lineups[_id] = Lineup(name, location, device, _type, postalCode)

    def new_mapping(self, lineup, station, channel, channelMinor, validFrom, validTo, onAirFrom, onAirTo):
        try:
            self.mappings[lineup].add(lineup, station, channel, channelMinor, validFrom, validTo, onAirFrom, onAirTo)
        except:
            m = Mapping()
            m.add(lineup, station, channel, channelMinor, validFrom, validTo, onAirFrom, onAirTo)
            self.mappings[lineup] = m

    def new_schedule(self, program, station, time, duration, new, stereo, subtitled, hdtv, closeCaptioned, ei, tvRating, dolby, partNumber, partTotal):
        try:
            self.schedules[station].add(program, time, duration, new, stereo, subtitled, hdtv, closeCaptioned, ei, tvRating, dolby, partNumber, partTotal)
        except:
            ss = Schedule_Station()
            ss.add(program, time, duration, new, stereo, subtitled, hdtv, closeCaptioned, ei, tvRating, dolby, partNumber, partTotal)
            self.schedules[station] = ss

    def new_program(self, _id, series, title, subtitle, description, mpaaRating, starRating, runTime, year, showType, colorCode, originalAirDate, syndicatedEpisodeNumber, advisories):
        self.programs[_id] = Program(series, title, subtitle, description, mpaaRating, starRating, runTime, year, showType, colorCode, originalAirDate, syndicatedEpisodeNumber, advisories)

    def new_crew_member(self, program, role, fullname, givenname, surname):
        try:
            self.crews[program].append(Crew_Member(role, fullname, givenname, surname))
        except:
            self.crews[program] = [Crew_Member(role, fullname, givenname, surname)]

    def new_genre(self, program, genre, relevance):
        try:
            self.genres[program].add(genre, relevance)
        except:
            self.genres[program] = Genre(genre, relevance)

    def new_xtvd(self, schemaVersion, validFrom, validTo):
        self.validFrom = sanitize_datetime(validFrom)
        self.validTo = sanitize_datetime(validTo)

    def printMsg(self, msg, error=False):
        if error:
            raise Exception(msg)

    def startItem(self, itemType):
        pass

    def newItem(self):
        pass

    def endItems(self):
        pass

