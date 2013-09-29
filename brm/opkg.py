from collections import namedtuple
import re
import tarfile

Package = namedtuple('Package', ['name', 'version', 'architecture'])
LocatedPackage = namedtuple('LocatedPackage', ['name', 'version', 'architecture', 'sha1'])

def parse_control_file(filename):
    with open(filename) as handle:
        return parse_control_handle(handle)

def parse_control_handle(handle):
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
    return Package(name=name, version=version, architecture=architecture)

def parse_ipk(filename):
    with tarfile.open(filename, 'r:gz') as tar_handle:
        control_tar_file = tar_handle.extractfile('./control.tar.gz')
        with tarfile.open(fileobj=control_tar_file) as control_tar_handle:
            control_file = control_tar_handle.extractfile('./control')
            return parse_control_handle(control_file)
