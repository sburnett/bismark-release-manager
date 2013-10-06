from collections import namedtuple
import logging
import re
import tarfile

import common
import release

def parse_control_file(filename):
    with open(filename) as handle:
        return parse_control_handle(handle)

def parse_control_handle(handle):
    logging.info('Parsing an ipk control file')
    contents = handle.read()
    field_pattern = re.compile(r'^(?P<key>\w+): (?P<value>.*)$', re.MULTILINE)
    name, version, architecture = None, None, None
    for match in field_pattern.finditer(contents):
        key = match.group('key')
        if key == 'Package':
            name = match.group('value')
        elif key == 'Version':
            version = match.group('value')
        elif key == 'Architecture':
            architecture = match.group('value')
    if name is None or version is None or architecture is None:
        logging.info('Missing name (%r), version (%r), or architecture (%r)',
                     name,
                     version,
                     architecture)
        return None
    return release.Package(name=name, version=version, architecture=architecture)

def parse_ipk(filename):
    logging.info('Parsing ipk %r', filename)
    with tarfile.open(filename, 'r:gz') as tar_handle:
        control_tar_file = tar_handle.extractfile('./control.tar.gz')
        with tarfile.open(fileobj=control_tar_file) as control_tar_handle:
            control_file = control_tar_handle.extractfile('./control')
            return parse_control_handle(control_file)

def fingerprint_package(filename):
    logging.info('Fingerprinting package %r', filename)
    package = parse_ipk(filename)
    if package is None:
        return None
    sha1 = common.get_fingerprint(filename)
    return release.FingerprintedPackage(
            name=package.name,
            version=package.version,
            architecture=package.architecture,
            sha1=sha1)

def locate_package(filename):
    logging.info('Locating package %r', filename)
    package = parse_ipk(filename)
    if package is None:
        return None
    return release.LocatedPackage(
            name=package.name,
            version=package.version,
            architecture=package.architecture,
            path=filename)
