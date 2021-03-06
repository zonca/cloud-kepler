#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pstats
import cProfile
import logging
import numpy as np
from utils import read_mapper_output, encode_array
#from bls_pulse_python import bls_pulse as bls_pulse_python
#from bls_pulse_vec import bls_pulse as bls_pulse_vec
from bls_pulse_cython import bls_pulse as bls_pulse_cython
from argparse import ArgumentParser
from configparser import SafeConfigParser, NoOptionError

# Basic logging configuration.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def __init_parser(defaults):
    '''
    Set up an argument parser for all possible command line options. Returns the
    parser object.

    :param defaults: Default values of each parameter
    :type defaults: dict

    :rtype: argparse.ArgumentParser
    '''
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', action='store', type=str, dest='config',
        help='Configuration file to read. Configuration supersedes command line arguments.')
    parser.add_argument('-p', '--segment', action='store', type=float, dest='segment',
        help='Trial segment (days). There is no default value.')
    parser.add_argument('-m', '--mindur', action='store', type=float, dest='mindur',
        default=float(defaults['min_duration']), help='[Optional] Minimum transit '
        'duration to search for (days).')
    parser.add_argument('-d', '--maxdur', action='store', type=float, dest='maxdur',
        default=float(defaults['max_duration']), help='[Optional] Maximum transit '
        'duration to search for (days).')
    parser.add_argument('-b', '--nbins', action='store', type=int, dest='nbins',
        default=int(defaults['n_bins']), help='[Optional] Number of bins to divide '
        'the lightcurve into.')
    parser.add_argument('--direction', action='store', type=int, dest='direction',
        default=bool(defaults['direction']), help='[Optional] Direction of box wave to '
        'look for. 1 = blip (top-hat), -1 = dip (drop), 0 = most significant, 2 = both.')
    parser.add_argument('--mode', action='store', type=str, dest='mode',
        default=defaults['mode'], help='[Optional] Implementation to use; python, '
        'vec, or cython.')
    parser.add_argument('-f', '--printformat', action='store', type=str, dest='fmt',
        default=defaults['print_format'], help='[Optional] Format of string printed to '
        'screen. Options are \'encoded\' (base-64 binary) or \'normal\' (human-readable '
        'ASCII strings). Set to any other string (e.g., \'none\') to supress output printing.')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
        default=bool(defaults['verbose']), help='[Optional] Turn on verbose messages/logging.')
    parser.add_argument('-x', '--profile', action='store_true', dest='profile',
        default=bool(defaults['profiling']), help='[Optional] Turn on speed profiling.')

    return parser


def __check_args(segment, mindur, maxdur, nbins, direction):
    '''
    Sanity-checks the input arguments; raises ValueError if any checks fail.

    :param segment: Length of a segment in days
    :type segment: float
    :param mindur: Minimum signal duration to consider in days
    :type mindur: float
    :param maxdur: Maximum signal duration to consider in days
    :type maxdur: float
    :param nbins: Number of bins per segment
    :type nbins: int
    :param direction: Signal direction to accept; -1 for dips, +1 for blips, 0 for best,
        or 2 for best dip and blip
    :type direction: int
    '''
    if segment <= 0.:
        raise ValueError('Segment size must be > 0.')
    if mindur <= 0.:
        raise ValueError('Minimum duration must be > 0.')
    if maxdur <= 0.:
        raise ValueError('Maximum duration must be > 0.')
    if maxdur <= mindur:
        raise ValueError('Maximum duration must be > minimum duration.')
    if nbins <= 0:
        raise ValueError('Number of bins must be > 0.')
    if direction not in [-1, 0, 1, 2]:
        raise ValueError('%d is not a valid value for direction.' % direction)


def main():
    '''
    Main function for this module. Parses all command line arguments, reads in data
    from stdin, and sends it to the proper BLS algorithm.
    '''
    # This is a global list of default values that will be used by the argument parser
    # and the configuration parser.
    defaults = {'min_duration':'0.0416667', 'max_duration':'0.5', 'n_bins':'100',
        'direction':'0', 'mode':'vec', 'print_format':'encoded', 'verbose':'0', 'profiling':'0'}

    # Set up the parser for command line arguments and read them.
    parser = __init_parser(defaults)
    args = parser.parse_args()

    if not args.config:
        # No configuration file specified -- read in command line arguments.
        if not args.segment:
            parser.error('No trial segment specified and no configuration file given.')

        segment = args.segment
        mindur = args.mindur
        maxdur = args.maxdur
        nbins = args.nbins
        direction = args.direction
        mode = args.mode
        fmt = args.fmt
        verbose = args.verbose
        profile = args.profile
    else:
        # Configuration file was given; read in that instead.
        cp = SafeConfigParser(defaults)
        cp.read(args.config)

        segment = cp.getfloat('DEFAULT', 'segment')
        mindur = cp.getfloat('DEFAULT', 'min_duration')
        maxdur = cp.getfloat('DEFAULT', 'max_duration')
        nbins = cp.getint('DEFAULT', 'n_bins')
        direction = cp.getint('DEFAULT', 'direction')
        mode = cp.get('DEFAULT', 'mode')
        fmt = cp.get('DEFAULT', 'print_format')
        verbose = cp.getboolean('DEFAULT', 'verbose')
        profile = cp.getboolean('DEFAULT', 'profiling')

    # Perform any sanity-checking on the arguments.
    __check_args(segment, mindur, maxdur, nbins, direction)

    # Send the data to the algorithm.
    for k, q, time, flux, fluxerr in read_mapper_output(sys.stdin):
        # Extract the array columns.
        time = np.array(time, dtype='float64')
        flux = np.array(flux, dtype='float64')
        fluxerr = np.array(fluxerr, dtype='float64')

        if profile:
            # Turn on profiling.
            pr = cProfile.Profile()
            pr.enable()

        if mode == 'python':
            raise NotImplementedError
            out = bls_pulse_python(time, flux, fluxerr, nbins, segment, mindur, maxdur,
                direction=direction)
        elif mode == 'vec':
            raise NotImplementedError
            out = bls_pulse_vec(time, flux, fluxerr, nbins, segment, mindur, maxdur,
                direction=direction)
        elif mode == 'cython':
            out = bls_pulse_cython(time, flux, fluxerr, nbins, segment, mindur, maxdur,
                direction=direction)
        else:
            raise ValueError('Invalid mode: %s' % mode)

        if profile:
            # Turn off profiling.
            pr.disable()
            ps = pstats.Stats(pr, stream=sys.stderr).sort_stats('time')
            ps.print_stats()

        if direction == 2:
            srsq_dip = out['srsq_dip']
            duration_dip = out['duration_dip']
            depth_dip = out['depth_dip']
            midtime_dip = out['midtime_dip']
            srsq_blip = out['srsq_blip']
            duration_blip = out['duration_blip']
            depth_blip = out['depth_blip']
            midtime_blip = out['midtime_blip']
            segstart = out['segstart']
            segend = out['segend']

            # Print output.
            if fmt == 'encoded':
                print "\t".join([k, q, encode_array(segstart), encode_array(segend), encode_array(srsq_dip),
                    encode_array(duration_dip), encode_array(depth_dip), encode_array(midtime_dip),
                    encode_array(srsq_blip), encode_array(duration_blip),
                    encode_array(depth_blip), encode_array(midtime_blip)])
            elif fmt == 'normal':
                print "-" * 120
                print "Kepler " + k
                print "Quarters: " + q
                print "-" * 120
                print '{0: <7s} {1: <13s} {2: <13s} {3: <13s} {4: <13s} {5: <13s} {6: <13s} {7: <13s} ' \
                    '{8: <13s}'.format('Segment', 'Dip SR^2', 'Dip dur.', 'Dip depth', 'Dip mid.',
                    'Blip SR^2', 'Blip dur.', 'Blip depth', 'Blip mid.')
                for i in xrange(len(srsq_dip)):
                    print '{0: <7d} {1: <13.6f} {2: <13.6f} {3: <13.6f} {4: <13.6f} ' \
                        '{5: <13.6f} {6: <13.6f} {7: <13.6f} {8: <13.6f}'.format(i,
                        srsq_dip[i], duration_dip[i], depth_dip[i], midtime_dip[i],
                        srsq_blip[i], duration_blip[i], depth_blip[i], midtime_blip[i])
                print "-" * 120
                print
                print
        else:
            srsq = out['srsq']
            duration = out['duration']
            depth = out['depth']
            midtime = out['midtime']
            segstart = out['segstart']
            segend = out['segend']

            # Print output.
            if fmt == 'encoded':
                print "\t".join([k, q, encode_array(segstart), encode_array(segend), encode_array(srsq),
                    encode_array(duration), encode_array(depth), encode_array(midtime)])
            elif fmt == 'normal':
                print "-" * 80
                print "Kepler " + k
                print "Quarters: " + q
                print "-" * 80
                print '{0: <7s} {1: <13s} {2: <10s} {3: <9s} {4: <13s}'.format('Segment',
                    'SR^2', 'Duration', 'Depth', 'Midtime')
                for i in xrange(len(srsq)):
                    print '{0: <7d} {1: <13.6f} {2: <10.6f} {3: <9.6f} {4: <13.6f}'.format(i,
                        srsq[i], duration[i], depth[i], midtime[i])
                print "-" * 80
                print
                print


if __name__ == '__main__':
    main()

