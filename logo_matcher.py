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

import unicodedata
import re
import collections
import os.path

debug = False

# These tokens get transposed for free
free_dict_defaults = {
   "int'l" : 'international',
   'television' : 'tv',
}

drop_token_defaults = {
    'a' : -0.1,
    'the' : -0.1,
    'feed' : -0.5,
    'pacific' : -0.2,
    'atlantic' : -0.2,
    'west' : -0.2,
    'east' : -0.2,
    'central' : -0.2,
    'hd' : -0.11,
    'sd' : -0.1,
    'tv' : -0.5,
    'channel' : -0.5,
    'network' : -0.5,
    'us' : -0.5,
    'usa' : -0.5,
    '1' : -1.0,
    '2' : -1.0,
    '3' : -1.0,
    '4' : -1.0,
    '5' : -1.0,
    '6' : -1.0,
    '7' : -1.0,
    '8' : -1.0,
    '9' : -1.0,

}

swap_token_defaults = {
    'overflow' : (-0.1, 'alternate'),
    'university' : (-0.1, 'u'),
    'dt' : (-0.5, 'tv'),
    'cd' : (-0.5, 'tv'),
}

resub_defaults = {
}

def dbg(*s):
    if debug:
        depth = s[0]
        s = [str(x) for x in s[1:]]
        print ' ' * depth * 4 + ' '.join(s)

class best_tracker(object):
    def __init__(self, score=None, val=None):
        self.score = score
        self.val = val
        self.other = []

    def merge(self, b):
        score, val = b.curr()
        if self.score is None or (score is not None and score > self.score):
            if self.score is not None:
                self.other.append(self.curr())
            self.score = score
            self.val = val
        elif score is not None:
            self.other.append(b.curr())
        self.other.extend(b.other)

    def add_score(self, delta):
        if self.val is not None:
            self.score += delta

    def prepend_token(self, tok, delta):
        if self.val is not None:
            self.val.insert(0, tok)
            self.score += delta

    def curr(self):
        return (self.score, self.val)

class matcher(object):
    def __init__(self, free={}, drop={}, add={}, resub={}, swap={}):
        self.source_stations = None
        self.target_stations = None
        self.mapping = dict()

        self.free_dict = dict(free.items() + free_dict_defaults.items())
        self.drop_tokens = dict(drop.items() + drop_token_defaults.items())
        if not add:
            add = drop;
        self.add_tokens = dict(add.items() + drop_token_defaults.items())
        self.resub = dict(resub_defaults.items() + resub.items())
        self.swap_tokens = dict(swap.items() + swap_token_defaults.items())
        rev = dict()
        for key, val in self.swap_tokens.iteritems():
            rev[val[1]] = (val[0], key)
        self.swap_tokens.update(rev)

    def find(self, td, tokens, depth=0, prefix=None, prefix_count=0, partial=False, generated=False, combined=False):
        best = best_tracker()
        if depth > 100:
            raise Exception('too deep')
        dbg(depth, 'find depth=%d tokens=%s prefix=%s prefix_count=%s partial=%s generated=%s' % (
                depth, str(tokens), str(prefix), prefix_count, str(partial), str(generated)), combined)

        orig_tokens = tokens

        if prefix:
            tok = prefix + tokens[0]
            if tokens[0]:
                tokens = tokens[1:]
        else:
            tok = tokens[0]
            tokens = tokens[1:]

        if not tokens and prefix is None and '' in td:
            dbg(depth, 'end', [])
            return best_tracker(0, [])

        if tok in td:# and prefix_count != 1:
            dbg(depth, 'direct', tok)
            ret = self.find(td[tok], tokens, depth + 1)
            ret.prepend_token(tok, 0)
            best.merge(ret)

        longest_common = 0
        if tok == 'strike':
            dbg(depth, 'custom', tok, td.keys())
        #dbg(depth, tok, td.keys())
        for t, sub in td.iteritems():

            if not t:
                continue

            if t in self.add_tokens:
                dbg(depth, 'adding token', t)
                ret = self.find(sub, orig_tokens, depth + 1, prefix=prefix,
                        prefix_count=prefix_count, partial=partial,
                        generated=generated, combined=combined)
                ret.prepend_token(t, self.add_tokens[t])
                best.merge(ret)

            common = os.path.commonprefix([t, tok])

            if tok == 'strike' and len(common):
                dbg(depth, 'custom', tok, common, t)

            if t == common and (not prefix or len(common) > len(prefix)) and tok != t:
                dbg(depth, 'our', tok, 'startswith', t)
                ret = self.find(sub, [tok[len(t):]] + tokens, depth + 1,
                        partial=False, generated=True, combined=(combined or prefix))
                ret.prepend_token(t, -0.1)
                best.merge(ret)

            if not prefix and len(common):
                if tok == common:
                    if prefix_count > 0 and not generated and len(common) == 1:
                        dbg(depth, '1their', t, 'and our', tok, 'share', common)
                        ret = self.find(sub, tokens, depth + 1, prefix_count=prefix_count+1, partial=True)
                        ret.prepend_token(t, -1.0 / len(t))
                        best.merge(ret)
                elif len(common) == 1 and not combined:
                    dbg(depth, '2their', t, 'and our', tok, 'share', common)
                    ret = self.find(sub, [tok[len(common):]] + tokens, depth + 1,
                            prefix_count=prefix_count+1, partial=True, combined=(combined or prefix))
                    ret.prepend_token(t, -1.0 / len(t))
                    best.merge(ret)

            if len(common) <= longest_common:
                continue

            # 'TruTV', ['Tru', 'TV']
            if tok == common and (not prefix or len(common) > len(prefix)):
                dbg(depth, 'their', t, 'startswith', tok)
                ret = self.find(td, tokens, depth + 1, prefix=tok, prefix_count=prefix_count+1)
                ret.add_score(-1.0 / len(t))
                best.merge(ret)

            if not partial and (not prefix or len(common) > len(prefix)):
                if (not prefix and len(common) == 1) or (prefix and len(common) == len(prefix) + 1):
                    dbg(depth, 'longest common1', common, tok, len(common))
                    ret = self.find(td, tokens, depth + 1, prefix=common, prefix_count=prefix_count+1)
                    ret.add_score(-1.0 / len(t))
                    best.merge(ret)

                if prefix_count > 1:
                    dbg(depth, 'longest common2', common, tok)
                    ret = self.find(td, [common] + tokens, depth + 1, combined=(combined or prefix))
                    ret.add_score(-1.0 / len(t))
                    best.merge(ret)

            longest_common = max(longest_common, len(common))

        if tok in self.drop_tokens and prefix_count != 1: #and not partial:
            dbg(depth, 'drop', tok)
            ret = self.find(td, tokens, depth + 1)
            ret.add_score(self.drop_tokens[tok])
            best.merge(ret)

        if tok in self.swap_tokens and prefix_count != 1 and not generated and not partial:
            score, swap = self.swap_tokens[tok]
            dbg(depth, 'swap', tok, swap)
            ret = self.find(td, [swap] + tokens, depth + 1, generated=True)
            ret.add_score(score)
            best.merge(ret)

        return best

    def normalize(self, s):
        for key, val in self.resub.iteritems():
            s = re.sub(key, val, s)

        # Remove everything in parens (Pacific, SD Feed, repeat of callsign)
        s = re.sub('\(.*\)', '', s)

        # Make string lowercase
        s = s.lower()

        # Split on number
        s = re.sub(r'(\D)(\d+)(\s|$)', '\g<1> \g<2><\g<3>', s)
        s = re.sub(r'(^|\s)(\d+)(\D)', '\g<1>\g<2> \g<3>', s)

        return s

    def tokenize(self, s):
        s = self.normalize(s)

        tokens = []
        for t in re.findall(r"[\w'\+]+", s, re.UNICODE):
            try:
                tokens.append(self.free_dict[t])
            except:
                tokens.append(t)

        # Special rules for squished together callsigns
        is_squished = len(tokens) < 4
        if is_squished:
            if len(tokens) == 3:
                try:
                    _ = int(tokens[2])
                except:
                    is_squished = False
        if is_squished:
            t = re.sub(r'(\S)(dt|cd|lp)$', '\g<1> \g<2>', tokens[0])
            if t != tokens[0]:
                tokens[0], t = t.split()
                tokens.insert(1, t)

        return tokens

    def set_target_stations(self, stations):
        if stations == self.target_stations:
            return
        self.target_stations = stations

        recursize_dd = lambda: collections.defaultdict(recursize_dd)
        self.token_dict = recursize_dd()
        self.station_dict = dict()
        for station in stations:
            d = self.token_dict
            tokens = self.tokenize(station)
            for t in tokens:
                d = d[t]

            # End signififier
            d = d['']
            self.station_dict[' '.join(tokens)] = station.strip()

        # Regenerate mapping
        if self.source_stations:
            self.mapping = dict()
            self.generate_mapping(self.source_stations)

    def lookup(self, station):
        # Cached
        try:
            return self.mapping[station]
        except:
            return None

    def generate_mapping(self, stations):
        # Remove any stale mappings
        for key in self.mapping.keys():
            if key not in self.source_stations:
                del self.mapping[key]

        self.source_stations = stations

        # Build cache
        for station in stations:
            tokens = self.tokenize(station)
            best = self.find(self.token_dict, tokens + [''])
            score, ret = best.curr()
            if score is not None:
                ret = ' '.join(ret)
                ret = self.station_dict[ret]
            self.mapping[station] = ret



