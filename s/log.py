from __future__ import absolute_import, print_function
import pprint
import logging
import logging.handlers
import s.func
import s.cached
import s.shell
import s.strings
import s.exceptions
import s.hacks
import s.bin.debug
import contextlib


_standard_format = '[%(levelname)s] [%(asctime)s] [%(name)s] [%(pathname)s] %(message)s'


_short_format = '[%(levelname)s] %(message)s'


for _name in ['debug', 'info', 'warn', 'warning', 'error', 'exception']:
    locals()[_name] = getattr(logging, _name)


def _make_handler(handler, level, format, pprint, filter=None):
    handler.setLevel(level.upper())
    if filter:
        handler.addFilter(filter())
    handler.setFormatter(_Formatter(format, pprint))
    return handler


def _get_format(format, short):
    return (format if format
            else _short_format if s.shell.override('--short') or short
            else _standard_format)


def _stream_handler(level, format):
    level = 'debug' if s.shell.override('--debug') else level
    return _make_handler(logging.StreamHandler(), level, format, pprint)


@s.cached.func
def setup(name=None, level='info', short=False, pprint=False, format=None, debug=False):
    # TODO how to make logging config immutable? no one should be able to manipulate logging after this call
    if debug:
        format = '%(message)s'
    for x in logging.root.handlers:
        logging.root.removeHandler(x)
    logging.root.addHandler(_stream_handler(level, _get_format(format, short)))


def _better_pathname(record):
    with s.exceptions.ignore():
        if ':' not in record.pathname:
            record.pathname = '/'.join(record.pathname.split('/')[-2:])
            record.pathname = '{}:{}'.format(record.pathname, record.lineno)
    return record


def _short_levelname(record):
    with s.exceptions.ignore():
        record.levelname = record.levelname.lower()[0]
    return record


def _process_record(record):
    if not hasattr(record, '_processed'):
        record = _better_pathname(record)
        record = _short_levelname(record)
        record._processed = True
    return record


class _Formatter(logging.Formatter):
    def __init__(self, fmt, pprint=False):
        self.pprint = pprint
        logging.Formatter.__init__(self, fmt=fmt)

    def format(self, record):
        record._pprint = self.pprint
        record = _process_record(record)
        return logging.Formatter.format(self, record)


@contextlib.contextmanager
def disable(*loggers):
    levels = []
    for name in loggers:
        assert isinstance(name, str), 'loggers must be a list of string names of loggers '
        logger = logging.getLogger(name)
        levels.append(logger.level)
        logger.setLevel('ERROR')
    try:
        yield
    except:
        raise
    finally:
        for level, name in zip(levels, loggers):
            logging.getLogger(name).setLevel(level)
