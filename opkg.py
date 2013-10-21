import logging
import os
import re
import tarfile

import common
import release


def parse_ipk(filename):
    logging.info('Parsing ipk %r', filename)
    contents = read_control_file_from_ipk(filename)
    return parse_package_from_control_contents(contents)


def parse_control_file(filename):
    logging.info('Parsing control file %r', filename)
    with open(filename) as handle:
        contents = handle.read()
    return parse_package_from_control_contents(contents)


def generate_package_index(filename):
    logging.info('Generating package index for %r', filename)
    contents = read_control_file_from_ipk(filename)

    basename = os.path.basename(filename)
    stat = os.stat(filename)
    file_size = stat.st_size
    md5sum = common.md5sum(filename)

    pattern = r'^Description:'
    replacement = 'Filename: %s\n' \
                  'Size: %d\n' \
                  'MD5Sum: %s\n' \
                  'Description:' % (basename, file_size, md5sum)
    return re.sub(pattern, replacement, contents, count=1, flags=re.MULTILINE)


def read_control_file_from_ipk(filename):
    logging.info('Parsing ipk %r', filename)
    with tarfile.open(filename, 'r:gz') as tar_handle:
        control_tar_file = tar_handle.extractfile('./control.tar.gz')
        with tarfile.open(fileobj=control_tar_file) as control_tar_handle:
            control_file = control_tar_handle.extractfile('./control')
            return control_file.read()


def parse_package_from_control_contents(contents):
    logging.info('Parsing an ipk control file')
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
