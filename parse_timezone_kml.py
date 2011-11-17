
from collections import defaultdict
try:
    import simplejson as json
except ImportError:
    import json
import math
from os import path
import sys
import time

def _get_from(what, data, start):
    start = data.index(what, start)
    start = data.index('<font COLOR=', start)
    start = nstart = data.index('>', start) + 1
    start = nend = data.index('</font>', start)
    return start, data[nstart:nend].strip()

def _get_coordinates(data, start):
    dstart = data.index('<coordinates>', start) + 13
    multi = data.find('<MultiGeometry>', start, dstart) != -1
    start = dend = data.index('</coordinates>', dstart)
    polygon = [
        map(float, pt.rpartition(',')[0].split(','))
            for pt in data[dstart:dend].split()
    ]
    return start, polygon, multi

def kmz_parser(ifname):
    '''
    Returns a list with the following format:
        [(tz_name, include, excludes),
         ...
         ]

    'include' is a list of (lon, lat) pairs is the outer boundary for the
    timezone.
    'excludes' is a potentially empty list of regions that is geometrically a
    "hole" cut out of the 'include' region. Not all timezones have excludes.

    Assuming that you have a function called contains(pt, region) that tells
    you whether a point is in a region, to determine whether a point is in a
    given timezone, you would perform:
        contains(pt, include) and not any(contains(pt, ex) for ex in excludes)
    '''
    print >>sys.stderr, time.asctime(), "Reading data"
    data = open(ifname, 'rb').read()
    print >>sys.stderr, time.asctime(), "Read %i bytes"%(len(data),)
    start = 0
    out = []
    exc = 0
    # We could parse the kml with an XML parser... then again, we know how the
    # data is formatted, so we save ourselves time and effort and just use
    # string.index() to bail when we run out of data
    while 1:
        try:
            start, name = _get_from('TZID', data, start)
            start, include, multi = _get_coordinates(data, start)
        except ValueError:
            break
        excludes = []
        if multi:
            end = data.find('TZID', start)
            if end == -1:
                end = len(data)
            end = data.rfind('</coordinates>', start, end)
            while start < end:
                try:
                    start, hole, multi = _get_coordinates(data, start)
                except ValueError:
                    break
                exc += 1
                excludes.append(hole)
        out.append((name, include, excludes))

    print >>sys.stderr, time.asctime(), "Loaded %i include and %i exclude regions from %s"%(len(out), exc, ifname)
    return out

def write_to_file(data, ofname):
    '''
    Write one large json blob that includes all of the timezone information.
    '''
    with open(ofname, 'wb') as out:
        json.dump(data, out)
    print >>sys.stdout, time.asctime(), "Wrote to", ofname

def write_to_path(data, opname):
    '''
    Write multiple json files, each of which includes an entire timezone.
    '''
    timezones = defaultdict(list)
    for chunk in data:
        timezones[chunk[0]].append(chunk)
    for name, chunk in sorted(timezones.iteritems()):
        write_to_file(chunk, path.join(opname, name.replace('/', '_')) + '.json')

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-o', '--out', action='store', dest='out', default=None,
        help='The output path (for multiple files, one file for each ' \
              'complete timezone) or the output file (for one file)')
    parser.add_option('-i', '--in', action='store', dest='inp', default=None,
        help='The kmz file to read as input')
    parser.add_option('-1', action='store_true', dest='one_file', default=False,
        help='Pass to output to a single file')
    options, args = parser.parse_args()

    if not options.out:
        print "Missing output path"
        raise SystemExit

    if not options.inp:
        print "Missing input file"
        raise SystemExit

    data = kmz_parser(options.inp)
    if options.one_file:
        write_to_file(data, options.out)
    else:
        write_to_path(data, options.out)
