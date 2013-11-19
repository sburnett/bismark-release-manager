from collections import namedtuple
import glob
import logging
import os
import shutil
import stat
import tempfile
import urllib2

import common
import opkg

Architecture = namedtuple('Architecture', ['name'])
PackageDirectory = namedtuple('PackageDirectory', ['name'])
FingerprintedImage = namedtuple(
    'FingerprintedImage', ['name', 'architecture', 'sha1'])
LocatedImage = namedtuple('LocatedImage', ['name', 'architecture', 'path'])

Package = namedtuple('Package', ['name', 'version', 'architecture'])

_FingerprintedPackage = namedtuple('FingerprintedPackage',
                                   ['name', 'version', 'architecture', 'sha1'])


class FingerprintedPackage(_FingerprintedPackage):

    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)

    @property
    def filename(self):
        return '%s_%s_%s.ipk' % (self.name, self.version, self.architecture)

_GroupPackage = namedtuple('GroupPackage',
                           ['group', 'name', 'version', 'architecture'])


class GroupPackage(_GroupPackage):

    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)


def new_bismark_release(path, build):
    logging.info('Creating new release in %r', path)
    release = _BismarkRelease(path)
    for name in build.architectures():
        release._architectures.add(Architecture(name))
    for dirname in build.package_directories():
        for filename in glob.iglob(os.path.join(dirname, '*.ipk')):
            release.add_package(filename)
    release._fingerprint_packages()
    release._builtin_packages.update(build.builtin_packages())
    for package in release.packages:
        if package.package in release.builtin_packages:
            continue
        release._extra_packages.add(package.package)
    for path, architecture in build.images():
        release.add_image(path, architecture)
    return release


def open_bismark_release(path):
    if not os.path.isdir(path):
        raise Exception('Release does not exist: %s' % path)
    return _BismarkRelease(path)


class _BismarkRelease(object):

    def __init__(self, path):
        self._path = path
        self._name = os.path.basename(path)
        self._packages_path = os.path.join(self._path, 'packages')
        self._images_path = os.path.join(self._path, 'images')

        self._architectures = common.NamedTupleSet(
            Architecture,
            self._full_path('architectures'))
        self._builtin_packages = common.NamedTupleSet(
            Package,
            self._full_path('builtin-packages'))
        self._extra_packages = common.NamedTupleSet(
            Package,
            self._full_path('extra-packages'))
        self._fingerprinted_packages = common.NamedTupleSet(
            FingerprintedPackage,
            self._full_path('fingerprinted-packages'))
        self._fingerprinted_images = common.NamedTupleSet(
            FingerprintedImage,
            self._full_path('fingerprinted-images'))
        self._package_upgrades = common.NamedTupleSet(
            GroupPackage,
            self._full_path('package-upgrades'))

    @property
    def name(self):
        return self._name

    @property
    def builtin_packages(self):
        return self._builtin_packages

    @property
    def extra_packages(self):
        return self._extra_packages

    @property
    def packages(self):
        return self._fingerprinted_packages

    @property
    def packages_path(self):
        return self._packages_path

    @property
    def images_path(self):
        return self._images_path

    @property
    def package_upgrades(self):
        return self._package_upgrades

    @property
    def images(self):
        return self._fingerprinted_images

    @property
    def architectures(self):
        return self._architectures

    def normalize_architecture(self, architecture):
        logging.info('normalizing architecture %r', architecture)
        if architecture != 'all':
            return [architecture]
        architectures = []
        for architecture in self._architectures:
            architectures.append(architecture.name)
        return architectures

    def locate_package(self, package):
        for fingerprinted_package in self._fingerprinted_packages:
            if package == fingerprinted_package.package:
                return os.path.join(self._packages_path,
                                    '%s.ipk' % fingerprinted_package.sha1)
        return None

    def update_base_build(self, build):
        for dirname in build.package_directories():
            for filename in glob.iglob(os.path.join(dirname, '*.ipk')):
                self.add_package(filename)
        self._fingerprint_packages()

    def add_package(self, import_path):
        if os.path.exists(import_path):
            self._add_package_real(import_path)
        else:
            logging.info("%s doesn't exist, so treating it as a URL.", import_path)
            with tempfile.NamedTemporaryFile(delete=True) as new_file:
                url_data = urllib2.urlopen(import_path)
                new_file.write(url_data.read())
                new_file.flush()
                self._add_package_real(new_file.name)

    def _add_package_real(self, filename):
        common.makedirs(self._packages_path)
        new_basename = '%s.ipk' % common.get_fingerprint(filename)
        new_filename = os.path.join(self._packages_path, new_basename)
        shutil.copy2(filename, new_filename)
        os.chmod(new_filename,
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        fingerprinted_package = opkg.fingerprint_package(new_filename)
        self._fingerprinted_packages.add(fingerprinted_package)

    def add_image(self, filename, architecture):
        common.makedirs(self._images_path)
        new_filename = os.path.join(
            self._images_path, os.path.basename(filename))
        shutil.copy2(filename, new_filename)

        name = os.path.basename(filename)
        sha1 = common.get_fingerprint(new_filename)
        self._fingerprinted_images.add(
            FingerprintedImage(name, architecture, sha1))

    def add_extra_package(self, *rest):
        extra_package = Package(*rest)
        self._extra_packages.add(extra_package)

    def remove_extra_package(self, *rest):
        extra_package = Package(*rest)
        self._extra_packages.remove(extra_package)

    def upgrade_package(self, group, name, version, architecture):
        existing_upgrade = None
        for group_package in self._package_upgrades:
            if group_package.group != group:
                continue
            if group_package.name != name:
                continue
            if group_package.architecture != architecture:
                continue
            existing_upgrade = group_package
        self._package_upgrades.discard(existing_upgrade)
        group_package = GroupPackage(group, name, version, architecture)
        self._package_upgrades.add(group_package)

    def save(self):
        common.makedirs(self._path)

        self.check_constraints()

        self._architectures.write_to_file()
        self._builtin_packages.write_to_file()
        self._extra_packages.write_to_file()
        self._fingerprinted_packages.write_to_file()
        self._fingerprinted_images.write_to_file()
        self._package_upgrades.write_to_file()

    def check_constraints(self):
        self._check_builtin_packages_exist()
        self._check_builtin_packages_unique()
        self._check_extra_packages_exist()
        self._check_builtin_extra_overlap()
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

    def _fingerprint_packages(self):
        logging.info('fingerinting packages in all package directories')
        for filename in glob.iglob(os.path.join(self._packages_path, '*.ipk')):
            fingerprinted_package = opkg.fingerprint_package(filename)
            self._fingerprinted_packages.add(fingerprinted_package)

    def _check_builtin_packages_exist(self):
        logging.info('checking that builtin packages exist')
        fingerprinted = set()
        for fingerprinted_package in self._fingerprinted_packages:
            fingerprinted.add(fingerprinted_package.package)
        for package in self._builtin_packages:
            if package not in fingerprinted:
                raise Exception('Cannot locate builtin package %s' % (
                    package,))

    def _check_extra_packages_exist(self):
        logging.info('checking that builtin packages exist')
        fingerprinted = set()
        for fingerprinted_package in self._fingerprinted_packages:
            fingerprinted.add(fingerprinted_package.package)
        for package in self._extra_packages:
            if package not in fingerprinted:
                raise Exception('Cannot locate extra package %s' % (
                    package,))

    def _check_builtin_extra_overlap(self):
        logging.info("checking if extra packages overlap with builtins")
        if self._extra_packages.intersection(self._builtin_packages):
            raise Exception('builtin and extra packages cannot overlap')

    def _check_builtin_packages_unique(self):
        logging.info('checking that builtin packages have only one version')
        package_keys = set()
        for package in self._builtin_packages:
            key = (package.name, package.architecture)
            if key in package_keys:
                raise Exception('Package %s (%s) has multiple versions' % key)
            package_keys.add(key)

    def _check_package_locations_exist(self):
        logging.info('checking that packages exist')
        for package in self._fingerprinted_packages:
            filename = os.path.join(self._packages_path,
                                    '%s.ipk' % package.sha1)
            if not os.path.isfile(filename):
                raise Exception('Cannot find package %s at %s' % (
                    package.name, package.path))

    def _check_package_locations_unique(self):
        logging.info('checking that package locations are unique')
        packages = set()
        for fingerprinted_package in self._fingerprinted_packages:
            package = fingerprinted_package.package
            if package in packages:
                raise Exception('Multiple locations for package %s' % (
                    package,))
            packages.add(package)

    def _check_package_fingerprints_valid(self):
        logging.info('checking that package fingerprints are valid')
        for filename in glob.iglob(os.path.join(self._packages_path, '*.ipk')):
            fingerprint, _ = os.path.splitext(os.path.basename(filename))
            if common.get_fingerprint(filename) != fingerprint:
                raise Exception('Fingerprint mismatch for %s' % filename)

    def _check_package_fingerprints_unique(self):
        logging.info('checking that package fingerprints are unique')
        packages = set()
        for fingerprinted_package in self._fingerprinted_packages:
            package = fingerprinted_package.package
            if package in packages:
                raise Exception(
                    'Multiple fingerprints for package %s' % package)
            packages.add(package)

    def _check_upgrades_exist(self):
        logging.info('checking that upgraded packages exists')
        fingerprinted = set()
        for fingerprinted_package in self._fingerprinted_packages:
            fingerprinted.add(fingerprinted_package.package)
        for group_package in self._package_upgrades:
            package = group_package.package
            if package not in fingerprinted:
                raise Exception(
                    'Cannot locate upgraded package %s' % (package,))

    def _check_upgrades_valid(self):
        logging.info('checking that upgrades only upgrade builting packages')
        package_keys = set()
        for package in self._builtin_packages:
            package_keys.add((package.name, package.architecture))
        for group_package in self._package_upgrades:
            key = (group_package.name, group_package.architecture)
            if key not in package_keys:
                raise Exception(
                    'upgrade %s is not for a builtin package' % group_package)

    def _check_upgrades_unique(self):
        logging.info('checking that upgraded packages are unique per node')
        all_upgrades = set()
        for group_package in self._package_upgrades:
            key = (group_package.group, group_package.name,
                   group_package.architecture)
            if key in all_upgrades:
                raise Exception('multiple upgrades to package %s for the same group %s' %
                                (group_package.name, group_package.group))

    def _check_upgrades_newer(self):
        # TODO: Parse and compare versions
        pass
