from collections import namedtuple
import csv
import errno
import glob
import logging
import os
import shutil

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

_NodePackage = namedtuple('NodePackage',
                          ['node', 'name', 'version', 'architecture'])
class NodePackage(_NodePackage):
    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)

PackageDirectory = namedtuple('PackageDirectory', ['name'])
FingerprintedImage = namedtuple('FingerprintedImage', ['name', 'architecture', 'sha1'])
LocatedImage = namedtuple('LocatedImage', ['name', 'architecture', 'path'])

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

def NewBismarkRelease(path, build):
    logging.info('Creating new release in %r', path)
    release = _BismarkRelease(path)
    for name in build.architectures():
        release._architectures.add(Architecture(name))
    release._builtin_packages.update(build.builtin_packages())
    for path, architecture in build.images():
        name = os.path.basename(path)
        release._located_images.add(LocatedImage(name, architecture, path))
        sha1 = common.get_fingerprint(path)
        release._fingerprinted_images.add(FingerprintedImage(name, architecture, sha1))
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
        self._name = os.path.basename(path)

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
        self._package_upgrades = NamedTupleSet(
                NodePackage,
                self._full_path('package-upgrades'))

    @property
    def builtin_packages(self):
        return self._builtin_packages

    @property
    def architectures(self):
        return self._architectures

    def get_upgrade(self, node, package, architecture):
        for node_package in self._package_upgrades:
            if node_package.node != node:
                continue
            if node_package.name != package:
                continue
            if node_package.architecture != architecture:
                continue
            return node_package

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

    def upgrade_package(self, node, name, version, architecture):
        existing_upgrade = None
        for node_package in self._package_upgrades:
            if node_package.node != node:
                continue
            if node_package.name != name:
                continue
            if node_package.architecture != architecture:
                continue
            existing_upgrade = node_package
        self._package_upgrades.discard(existing_upgrade)
        node_package = NodePackage(node, name, version, architecture)
        self._package_upgrades.add(node_package)

    def deploy_packages(self, deployment_path):
        for located_package in self._located_packages:
            destination = os.path.join(deployment_path,
                                       'packages',
                                       located_package.architecture)
            common.makedirs(destination)
            shutil.copy2(located_package.path, destination)

    def deploy_images(self, deployment_path):
        for located_image in self._located_images:
            destination_dir = os.path.join(deployment_path,
                                           self._name,
                                           located_image.architecture)
            common.makedirs(destination_dir)
            shutil.copy2(located_image.path, destination_dir)

    def deploy_builtin_packages(self, deployment_path):
        package_paths = self._deployment_package_paths(deployment_path)
        for package in self._builtin_packages:
            source = package_paths[package]
            architectures = self._normalize_architecture(package.architecture)
            for architecture in architectures:
                link_dir = os.path.join(deployment_path,
                                        architecture,
                                        'packages')
                common.makedirs(link_dir)
                link_name = os.path.join(link_dir, os.path.basename(source))
                relative_source = os.path.relname(source, link_dir)
                os.symlink(relative_source, link_name)

    def deploy_upgrades(self, deployment_path):
        upgraded_packages = self._normalize_package_upgrades()
        package_paths = self._deployment_package_paths(deployment_path)
        for node_package in upgraded_packages:
            package = node_package.package
            source = package_paths[package]
            architectures = self._normalize_architecture(node_package.architecture)
            for architecture in architectures:
                link_dir = os.path.join(deployment_path,
                                        self._name,
                                        architecture,
                                        'updates-device',
                                        node_package.node)
                common.makedirs(link_dir)
                link_name = os.path.join(link_dir, os.path.basename(source))
                relative_source = os.path.relpath(source, link_dir)
                os.symlink(relative_source, link_name)

        pattern = os.path.join(deployment_path, '*', 'updates-device', '*')
        for dirname in glob.iglob(pattern):
            if not os.path.isdir(dirname):
                continue
            with open(os.path.join(dirname, 'Upgradable'), 'w') as handle:
                pass

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
        self._package_upgrades.write_to_file()

    def check_constraints(self):
        self._check_package_directories_exist()
        self._check_builtin_packages_exist()
        self._check_builtin_packages_unique()
        self._check_package_locations_exist()
        self._check_package_locations_unique()
        self._check_package_fingerprints_valid()
        self._check_package_fingerprints_unique()
        self._check_upgrades_exist()
        self._check_upgrades_valid()
        self._check_upgrades_unique()
        self._check_upgrades_newer()

    def _full_path(self, basename):
        return os.path.join(self._path, basename)

    def _locate_packages(self):
        logging.info('Locating packages in all package directories')
        for package_directory in self._package_directories:
            pattern = os.path.join(package_directory.name, '*.ipk')
            for filename in glob.iglob(pattern):
                located_package = opkg.locate_package(filename)
                self._located_packages.add(located_package)

    def _fingerprint_packages(self):
        logging.info('Fingerinting packages in all package directories')
        for package_directory in self._package_directories:
            pattern = os.path.join(package_directory.name, '*.ipk')
            for filename in glob.iglob(pattern):
                fingerprinted_package = opkg.fingerprint_package(filename)
                self._fingerprinted_packages.add(fingerprinted_package)

    def _normalize_architecture(self, architecture):
        if architecture != 'all':
            return [architecture]
        architectures = []
        for architecture in self.architectures:
            architectures.add(architecture.name)
        return architectures

    def _normalize_package_upgrades(self):
        nodes = set()
        for node_package in self._package_upgrades:
            nodes.add(node_package.node)
        upgrades = defaultdict(dict)
        for node_package in self._package_upgrades:
            if node_package.node == 'default':
                continue
            key = (node_package.name, node_package.architecture)
            upgrades[key][node_package.node] = node_package.version
        for node_package in self._package_upgrades:
            if node_package.node != 'default':
                continue
            key = (node_package.name, node_package.architecture)
            for node in nodes:
                if node in upgrades[key]:
                    continue
                upgrades[key][node] = node_package.version
        upgraded_packages = set()
        for (name, architecture), nodes in upgrades.items():
            for node, version in nodes.items():
                node_package = NodePackage(node, name, version, architecture)
                upgraded_packages.add(node_package)
        return upgraded_packages

    def _deployment_package_paths(self, deployment_path):
        package_paths = dict()
        for located_package in self._located_packages:
            package_path = os.path.join(
                    deployment_path,
                    'packages',
                    self._name,
                    located_package.architecture,
                    os.path.basename(located_package.path))
            package_paths[located_package.package] = package_path
        return package_paths

    def _check_package_directories_exist(self):
        logging.info('Checking that package directories exist')
        for package_directory in self._package_directories:
            if not os.path.isdir(package_directory.name):
                raise Exception('Package directory %s does not exist' % name)

    def _check_builtin_packages_exist(self):
        logging.info('Checking that builtin packages exist')
        located = set()
        for located_package in self._located_packages:
            located.add(located_package.package)
        for package in self._builtin_packages:
            if package not in located:
                raise Exception('Cannot locate builtin package %s' % key)

    def _check_builtin_packages_unique(self):
        logging.info('Checking that builtin packages have only one version')
        package_keys = set()
        for package in self._builtin_packages:
            key = (package.name, package.architecture)
            if key in package_keys:
                raise Exception('Package %s (%s) has multiple versions' % key)
            package_keys.add(key)

    def _check_package_locations_exist(self):
        logging.info('Checking that located packages exist')
        for package in self._located_packages:
            if not os.path.isfile(package.path):
                raise Exception('Cannot find package %s at %s' % (package.name, package.path))

    def _check_package_locations_unique(self):
        logging.info('Checking that package locations are unique')
        packages = set()
        for located_package in self._located_packages:
            package = located_package.package
            if package in packages:
                raise Exception('Multiple locations for package %s' % package)
            packages.add(package)

    def _check_package_fingerprints_valid(self):
        logging.info('Checking that package fingerprints are valid')
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
        logging.info('Checking that package fingerprints are unique')
        packages = set()
        for fingerprinted_package in self._fingerprinted_packages:
            package = fingerprinted_package.package
            if package in packages:
                raise Exception('Multiple fingerprints for package %s' % package)
            packages.add(package)

    def _check_upgrades_exist(self):
        logging.info('Checking that upgraded packages exists')
        located = set()
        for located_package in self._located_packages:
            located.add(located_package.package)
        for node_package in self._package_upgrades:
            package = node_package.package
            if package not in located:
                raise Exception('Cannot locate upgraded package %s' % (package,))

    def _check_upgrades_valid(self):
        logging.info('Checking that upgrades only upgrade builting packages')
        package_keys = set()
        for package in self._builtin_packages:
            package_keys.add((package.name, package.architecture))
        for node_package in self._package_upgrades:
            key = (node_package.name, node_package.architecture)
            if key not in package_keys:
                raise Exception('upgrade %s is not for a builtin package' % node_package)

    def _check_upgrades_unique(self):
        logging.info('Checking that upgraded packages are unique per node')
        all_upgrades = set()
        for node_package in self._package_upgrades:
            key = (node_package.node, node_package.name, node_package.architecture)
            if key in all_upgrades:
                raise Exception('multiple upgrades to package %s for the same node %s' % (node_package.name, node_package.node))

    def _check_upgrades_newer(self):
        # TODO: Parse and compare versions
        pass
