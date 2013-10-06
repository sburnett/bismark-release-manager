import hashlib

def get_fingerprint(filename):
    with open(filename) as handle:
        contents = handle.read()
    hasher = hashlib.sha1()
    hasher.update(contents)
    return hasher.hexdigest()
