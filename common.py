from collections import defaultdict
import csv
import errno
import hashlib
import logging
import os
import StringIO
import sys


def get_fingerprint(filename):
    with open(filename) as handle:
        contents = handle.read()
    hasher = hashlib.sha1()
    hasher.update(contents)
    return hasher.hexdigest()


def md5sum(filename):
    with open(filename) as handle:
        contents = handle.read()
    hasher = hashlib.md5()
    hasher.update(contents)
    return hasher.hexdigest()


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            pass
        else:
            raise

class ColumnFormatter(object):
    def __init__(self, prefix=''):
        self._buffer = StringIO.StringIO()
        self._prefix = prefix

    def write(self, s):
        self._buffer.write(s)

    def close(self):
        lines = self._buffer.getvalue().splitlines()
        lines.sort()

        column_widths = defaultdict(int)
        for line in lines:
            words = line.split()
            for c, word in enumerate(words):
                column_widths[c] = max(column_widths[c], len(word))
        for line in lines:
            words = line.split()
            sys.stdout.write(self._prefix)
            for c, word in enumerate(words):
                format_string = '%%-%ds' % column_widths[c]
                print format_string % word,
            print

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class NamedTupleSet(set):

    def __init__(self, tuple_type, filename):
        self._tuple_type = tuple_type
        self._filename = filename
        if os.path.isfile(self._filename):
            self.read_from_file()

    def read_from_file(self):
        logging.info('Reading namedtuple from file %r', self._filename)
        with open(self._filename) as handle:
            for row in csv.DictReader(handle, delimiter=' '):
                self.add(self._tuple_type(**row))

    def write_to_file(self):
        logging.info('Writing namedtuple to file %r', self._filename)
        with open(self._filename, 'w') as handle:
            writer = csv.DictWriter(handle,
                                    self._tuple_type._fields,
                                    delimiter=' ')
            writer.writeheader()
            for record in sorted(self):
                writer.writerow(record._asdict())
