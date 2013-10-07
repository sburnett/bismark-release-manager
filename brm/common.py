import errno
import hashlib
import os

def get_fingerprint(filename):
    with open(filename) as handle:
        contents = handle.read()
    hasher = hashlib.sha1()
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
