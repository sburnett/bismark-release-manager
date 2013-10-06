from collections import namedtuple
import csv
import errno
import glob
import os

import common
import opkg

Architecture = namedtuple('Architecture', ['name'])
_Package = namedtuple('Package', ['name', 'version', 'architecture'])
class Package(_Package):
    def located_package(self, filename):
        return LocatedPackage(self.name, self.version, self.architecture, filename)

_FingerprintedPackage = namedtuple('FingerprintedPackage',
                                   ['name', 'version', 'architecture', 'sha1'])
class FingerprintedPackage(_FingerprintedPackage):
    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)

_LocatedPackage = namedtuple('LocatedPackage',
                             ['name', 'version', 'architecture', 'path'])
class LocatedPackage(_LocatedPackage):
    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)

PackageDirectory = namedtuple('PackageDirectory', ['name'])
FingerprintedImage = namedtuple('FingerprintedImage', ['name', 'sha1'])
LocatedImage = namedtuple('LocatedImage', ['name', 'path'])

class NamedTupleSet(set):
    def __init__(self, tuple_type, filename):
        self._tuple_type = tuple_type
        self._filename = filename
        if os.path.isfile(self._filename):
            self.read_from_file()

    def read_from_file(self):
        with open(self._filename) as handle:
            for row in csv.DictReader(handle, delimiter=' '):
                self.add(self._tuple_type(**row))

    def write_to_file(self):
        with open(self._filename, 'w') as handle:
            writer = csv.DictWriter(handle,
                                    self._tuple_type._fields,
                                    delimiter=' ')
            writer.writeheader()
            for record in sorted(self):
                writer.writerow(record._asdict())

def NewBismarkRelease(path, build):
    release = _BismarkRelease(path)
    for name in build.architectures():
        release._architectures.add(Architecture(name))
    release._builtin_packages.update(build.builtin_packages())
    for path in build.images():
        name = os.path.basename(path)
        release._located_images.add(LocatedImage(name, path))
        sha1 = common.get_fingerprint(path)
        release._fingerprinted_images.add(FingerprintedImage(name, sha1))
    for name in build.package_directories():
        release._package_directories.add(PackageDirectory(name))
    release._locate_packages()
    release._fingerprint_packages()
    return release

def BismarkRelease(path):
    if not os.path.isdir(path):
        raise Exception('Release does not exist: %s' % path)
    return _BismarkRelease(path)

class _BismarkRelease(object):
    def __init__(self, path):
        self._path = path

        self._architectures = NamedTupleSet(
                Architecture,
                self._full_path('architectures'))
        self._builtin_packages = NamedTupleSet(
                Package,
                self._full_path('builtin-packages'))
        self._fingerprinted_packages = NamedTupleSet(
                FingerprintedPackage,
                self._full_path('fingerprinted-packages'))
        self._located_packages = NamedTupleSet(
                LocatedPackage,
                self._full_path('located-packages'))
        self._package_directories = NamedTupleSet(
                PackageDirectory,
                self._full_path('package-directories'))
        self._fingerprinted_images = NamedTupleSet(
                FingerprintedImage,
                self._full_path('fingerprinted-images'))
        self._located_images = NamedTupleSet(
                LocatedImage,
                self._full_path('located-images'))

    @property
    def builtin_packages(self):
        return self._builtin_packages

    @property
    def architectures(self):
        return self._architectures

    def update_base_build(self, build):
        for name in build.package_directories():
            self._package_directories.add(PackageDirectory(name))
        self._locate_packages()
        self._fingerprint_packages()

    def add_package(self, filename):
        package = opkg.parse_ipk(filename)
        located_package = package.located_package(filename)
        self._located_packages.add(located_package)
        fingerprinted_package = opkg.fingerprint_package(filename)
        self._fingerprinted_packages.add(fingerprinted_package)

    def save(self):
        try:
            os.makedirs(self._path)
        except OSError as err:
            if err.errno == errno.EEXIST:
                pass
            else:
                raise

        self.check_constraints()

        self._architectures.write_to_file()
        self._builtin_packages.write_to_file()
        self._fingerprinted_packages.write_to_file()
        self._located_packages.write_to_file()
        self._package_directories.write_to_file()
        self._fingerprinted_images.write_to_file()
        self._located_images.write_to_file()

    def check_constraints(self):
        self._check_package_directories_exist()
        self._check_builtin_packages_exist()
        self._check_builtin_packages_unique()
        self._check_package_locations_exist()
        self._check_package_locations_unique()
        self._check_package_fingerprints_valid()
        self._check_package_fingerprints_unique()

    def _full_path(self, basename):
        return os.path.join(self._path, basename)

    def _locate_packages(self):
        for package_directory in self._package_directories:
            pattern = os.path.join(package_directory.name, '*.ipk')
            for filename in glob.iglob(pattern):
                located_package = opkg.locate_package(filename)
                self._located_packages.add(located_package)

    def _fingerprint_packages(self):
        for package_directory in self._package_directories:
            pattern = os.path.join(package_directory.name, '*.ipk')
            for filename in glob.iglob(pattern):
                fingerprinted_package = opkg.fingerprint_package(filename)
                self._fingerprinted_packages.add(fingerprinted_package)

    def _check_package_directories_exist(self):
        for package_directory in self._package_directories:
            if not os.path.isdir(package_directory.name):
                raise Exception('Package directory %s does not exist' % name)

    def _check_builtin_packages_exist(self):
        located = set()
        for located_package in self._located_packages:
            located.add(located_package.package)
        for package in self._builtin_packages:
            if package not in located:
                raise Exception('Cannot locate builtin package %s' % key)

    def _check_builtin_packages_unique(self):
        package_keys = set()
        for package in self._builtin_packages:
            key = (package.name, package.architecture)
            if key in package_keys:
                raise Exception('Package %s (%s) has multiple versions' % key)
            package_keys.add(key)

    def _check_package_locations_exist(self):
        for package in self._located_packages:
            if not os.path.isfile(package.path):
                raise Exception('Cannot find package %s at %s' % (package.name, package.path))

    def _check_package_locations_unique(self):
        packages = set()
        for located_package in self._located_packages:
            package = located_package.package
            if package in packages:
                raise Exception('Multiple locations for package %s' % package)
            packages.add(package)

    def _check_package_fingerprints_valid(self):
        fingerprints = {}
        for fingerprinted_package in self._fingerprinted_packages:
            fingerprints[fingerprinted_package.package] = fingerprinted_package.sha1
        for located_package in self._located_packages:
            if located_package.package not in fingerprints:
                raise Exception('Missing fingerprint for %s' % key)
            old_sha1 = fingerprints[located_package.package]
            new_sha1 = common.get_fingerprint(located_package.path)
            if old_sha1 != new_sha1:
                raise Exception('Fingerprint mismatch for %s: %s vs %s' % (key, old_sha1, new_sha1))

    def _check_package_fingerprints_unique(self):
        packages = set()
        for fingerprinted_package in self._fingerprinted_packages:
            package = fingerprinted_package.package
            if package in packages:
                raise Exception('Multiple fingerprints for package %s' % package)
            packages.add(package)
