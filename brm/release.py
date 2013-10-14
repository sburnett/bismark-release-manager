from collections import defaultdict, namedtuple
import glob
import gzip
import logging
import os
import shutil
import StringIO

import common
import opkg

Architecture = namedtuple('Architecture', ['name'])
PackageDirectory = namedtuple('PackageDirectory', ['name'])
FingerprintedImage = namedtuple('FingerprintedImage', ['name', 'architecture', 'sha1'])
LocatedImage = namedtuple('LocatedImage', ['name', 'architecture', 'path'])

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

_GroupPackage = namedtuple('GroupPackage',
                           ['group', 'name', 'version', 'architecture'])
class GroupPackage(_GroupPackage):
    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)

_NodePackage = namedtuple('NodePackage',
                          ['node', 'name', 'version', 'architecture'])
class NodePackage(_NodePackage):
    @property
    def package(self):
        return Package(self.name, self.version, self.architecture)

def bool_to_string(b):
    if b:
        return '1'
    else:
        return '0'

def new_bismark_release(path, build):
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

def open_bismark_release(path):
    if not os.path.isdir(path):
        raise Exception('Release does not exist: %s' % path)
    return _BismarkRelease(path)

class _BismarkRelease(object):
    def __init__(self, path):
        self._path = path
        self._name = os.path.basename(path)

        self._architectures = common.NamedTupleSet(
                Architecture,
                self._full_path('architectures'))
        self._builtin_packages = common.NamedTupleSet(
                Package,
                self._full_path('builtin-packages'))
        self._fingerprinted_packages = common.NamedTupleSet(
                FingerprintedPackage,
                self._full_path('fingerprinted-packages'))
        self._located_packages = common.NamedTupleSet(
                LocatedPackage,
                self._full_path('located-packages'))
        self._package_directories = common.NamedTupleSet(
                PackageDirectory,
                self._full_path('package-directories'))
        self._fingerprinted_images = common.NamedTupleSet(
                FingerprintedImage,
                self._full_path('fingerprinted-images'))
        self._located_images = common.NamedTupleSet(
                LocatedImage,
                self._full_path('located-images'))
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
    def packages(self):
        return self._located_packages

    @property
    def architectures(self):
        return self._architectures

    def get_upgrade(self, group, package, architecture):
        for group_package in self._package_upgrades:
            if group_package.group != group:
                continue
            if group_package.name != package:
                continue
            if group_package.architecture != architecture:
                continue
            return group_package

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

    def deploy_packages(self, deployment_path):
        for located_package in self._located_packages:
            destination = os.path.join(deployment_path,
                                       'packages',
                                       self._name,
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
                                        self._name,
                                        architecture,
                                        'packages')
                common.makedirs(link_dir)
                link_name = os.path.join(link_dir, os.path.basename(source))
                relative_source = os.path.relpath(source, link_dir)
                os.symlink(relative_source, link_name)

    def deploy_upgrades(self, node_groups, deployment_path):
        resolved_upgrades = self._resolve_groups_to_nodes(
                node_groups,
                self._package_upgrades)
        upgraded_packages = self._normalize_default_packages(resolved_upgrades)
        self._symlink_packages(upgraded_packages,
                               'updates-device',
                               deployment_path)

    def deploy_experiment_packages(self,
                                   experiments,
                                   node_groups,
                                   deployment_path):

        all_group_packages = set()
        for name in experiments.experiments:
            experiment = experiments.experiment(name)
            for group_package in experiment.packages:
                if group_package.release != self._name:
                    continue
                all_group_packages.add(group_package)
        node_packages = self._resolve_groups_to_nodes(node_groups,
                                                      all_group_packages)
        normalized_packages = self._normalize_default_packages(node_packages)
        self._symlink_packages(normalized_packages,
                               'experiments-device',
                               deployment_path)

    def deploy_experiment_configurations(self,
                                         experiments,
                                         node_groups,
                                         deployment_path):
        group_configuration_headers = defaultdict(dict)
        for name in experiments.experiments:
            experiment = experiments.experiment(name)
            for group in experiment.groups:
                s = StringIO.StringIO()
                print >>s, "config 'experiment' '%s'" % experiment.name
                print >>s, "    option 'display_name' '%s'" % experiment.display_name
                print >>s, "    option 'description' '%s'" % experiment.description
                for conflict in experiment.conflicts:
                    print >>s, "    list 'conflicts' '%s'" % conflict
                required = bool_to_string(experiment.is_required(group))
                print >>s, "    option 'required' '%s'" % required
                revoked = bool_to_string(experiment.is_revoked(group))
                print >>s, "    option 'revoked' '%s'" % revoked
                installed = bool_to_string(experiment.is_installed_by_default(group))
                print >>s, "    option 'installed' '%s'" % installed
                group_configuration_headers[group][name] = s.getvalue()

        node_configuration_headers = defaultdict(dict)
        for group, headers in group_configuration_headers.items():
            nodes = self._resolve_group_to_nodes(node_groups, group)
            for node in nodes:
                for experiment, header in headers.items():
                    if experiment in node_configuration_headers[node]:
                        raise Exception('conflicting experiment defintions')
                    node_configuration_headers[node][experiment] = header
        normalized_headers = self._normalize_default_experiments(
                node_configuration_headers)

        group_experiment_packages = defaultdict(lambda: defaultdict(set))
        for name in experiments.experiments:
            experiment = experiments.experiment(name)
            for group_package in experiment.packages:
                if group_package.release != self._name:
                    continue
                group_experiment_packages[group_package.group][name].add(group_package)

        bodies = defaultdict(dict)
        for group, experiment_packages in group_experiment_packages.items():
            nodes = self._resolve_group_to_nodes(node_groups, group)
            for node in nodes:
                for experiment, packages in experiment_packages.items():
                    for package in packages:
                        architectures = self._normalize_architecture(
                                package.architecture)
                        for architecture in architectures:
                            key = architecture, experiment, package.name
                            if key in bodies[node]:
                                raise Exception('conflicting packages for experiment')
                            bodies[node][key] = package
        normalized_bodies = self._normalize_default_experiments(bodies)

        configurations = defaultdict(dict)
        for node, packages in normalized_bodies.items():
            for architecture, experiment, name in packages:
                if experiment not in configurations[architecture, node]:
                    configurations[architecture, node][experiment] = (
                            normalized_headers[node][experiment])
                configurations[architecture, node][experiment] += (
                        "    list 'package' '%s'\n" % name)

        for (architecture, node), experiments in configurations.items():
            filename = os.path.join(deployment_path,
                                    self.name,
                                    architecture,
                                    'experiments-device',
                                    node,
                                    'Experiments')
            common.makedirs(os.path.dirname(filename))
            with open(filename, 'w') as handle:
                for name, configuration in sorted(experiments.items()):
                    handle.write(configuration)
                    print >>handle, ''

    def deploy_packages_gz(self, deployment_path):
        patterns = [
                '*/*/experiments-device/*',
                '*/*/packages',
                '*/*/updates-device/*',
                ]
        for pattern in patterns:
            full_pattern = os.path.join(deployment_path, pattern)
            for dirname in glob.iglob(full_pattern):
                package_indices = []
                for filename in glob.iglob(os.path.join(dirname, '*.ipk')):
                    package_index = opkg.generate_package_index(filename)
                    package_indices.append(package_index)
                index_contents = '\n'.join(package_indices)
                index_filename = os.path.join(dirname, 'Packages.gz')
                with gzip.open(index_filename, 'wb') as handle:
                    handle.write(index_contents)

    def deploy_upgradable_sentinels(self, deployment_path):
        patterns = [
                '*/*/updates-device/*',
                '*/*/experiments-device/*',
                ]
        for pattern in patterns:
            full_pattern = os.path.join(deployment_path, pattern)
            for dirname in glob.iglob(full_pattern):
                if not os.path.isdir(dirname):
                    continue
                with open(os.path.join(dirname, 'Upgradable'), 'w') as handle:
                    pass

    def save(self):
        common.makedirs(self._path)

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
        logging.info('locating packages in all package directories')
        for package_directory in self._package_directories:
            pattern = os.path.join(package_directory.name, '*.ipk')
            for filename in glob.iglob(pattern):
                located_package = opkg.locate_package(filename)
                self._located_packages.add(located_package)

    def _fingerprint_packages(self):
        logging.info('fingerinting packages in all package directories')
        for package_directory in self._package_directories:
            pattern = os.path.join(package_directory.name, '*.ipk')
            for filename in glob.iglob(pattern):
                fingerprinted_package = opkg.fingerprint_package(filename)
                self._fingerprinted_packages.add(fingerprinted_package)

    def _normalize_architecture(self, architecture):
        logging.info('normalizing architecture %r', architecture)
        if architecture != 'all':
            return [architecture]
        architectures = []
        for architecture in self.architectures:
            architectures.append(architecture.name)
        return architectures

    def _resolve_group_to_nodes(self, node_groups, group_or_node):
        if group_or_node in node_groups.groups:
            logging.info('resolving %r to a set of nodes', group_or_node)
            return node_groups.nodes_in_group(group_or_node)
        else:
            logging.info('resolving %r to a single node', group_or_node)
            return [group_or_node]

    def _resolve_groups_to_nodes(self, node_groups, group_packages):
        logging.info('resolving groups to nodes')
        node_packages = set()
        for group_package in group_packages:
            for node in self._resolve_group_to_nodes(node_groups, group_package.group):
                node_package = NodePackage(node,
                                           group_package.name,
                                           group_package.version,
                                           group_package.architecture)
                node_packages.add(node_package)

        # TODO(sburnett): Change this to pick the latest version instead of
        # throwing an error.
        packages_per_node = set()
        for package in node_packages:
            key = (package.node, package.name, package.architecture)
            if key in packages_per_node:
                raise Exception('Conflicting package versions for a node')
            packages_per_node.add(key)

        return node_packages

    def _normalize_default_packages(self, node_packages):
        logging.info('normalizing packages')
        nodes = set()
        for node_package in node_packages:
            nodes.add(node_package.node)
        packages = defaultdict(dict)
        for node_package in node_packages:
            if node_package.node == 'default':
                continue
            key = (node_package.name, node_package.architecture)
            packages[key][node_package.node] = node_package.version
        for node_package in node_packages:
            if node_package.node != 'default':
                continue
            key = (node_package.name, node_package.architecture)
            for node in nodes:
                if node in packages[key]:
                    continue
                packages[key][node] = node_package.version
        normalized_packages = set()
        for (name, architecture), nodes in packages.items():
            for node, version in nodes.items():
                node_package = NodePackage(node, name, version, architecture)
                normalized_packages.add(node_package)
        return normalized_packages

    def _normalize_default_experiments(self, node_dicts):
        logging.info('normalizing experiments')
        if 'default' not in node_dicts:
            return node_dicts
        default_dict = node_dicts['default']
        for key, default_value in default_dict.items():
            for node, value_dict in node_dicts.items():
                if node == 'default':
                    continue
                if key in value_dict:
                    continue
                value_dict[key] = default_value
        return node_dicts

    def _deployment_package_paths(self, deployment_path):
        logging.info('locating package in deployed path')
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

    def _symlink_packages(self, packages, subdirectory, deployment_path):
        package_paths = self._deployment_package_paths(deployment_path)
        for package in packages:
            source = package_paths[package.package]
            architectures = self._normalize_architecture(package.architecture)
            for architecture in architectures:
                link_dir = os.path.join(deployment_path,
                                        self._name,
                                        architecture,
                                        subdirectory,
                                        package.node)
                common.makedirs(link_dir)
                link_name = os.path.join(link_dir, os.path.basename(source))
                relative_source = os.path.relpath(source, link_dir)
                os.symlink(relative_source, link_name)

    def _check_package_directories_exist(self):
        logging.info('checking that package directories exist')
        for package_directory in self._package_directories:
            if not os.path.isdir(package_directory.name):
                raise Exception('Package directory %s does not exist' % name)

    def _check_builtin_packages_exist(self):
        logging.info('checking that builtin packages exist')
        located = set()
        for located_package in self._located_packages:
            located.add(located_package.package)
        for package in self._builtin_packages:
            if package not in located:
                raise Exception('Cannot locate builtin package %s' % (package,))

    def _check_builtin_packages_unique(self):
        logging.info('checking that builtin packages have only one version')
        package_keys = set()
        for package in self._builtin_packages:
            key = (package.name, package.architecture)
            if key in package_keys:
                raise Exception('Package %s (%s) has multiple versions' % key)
            package_keys.add(key)

    def _check_package_locations_exist(self):
        logging.info('checking that located packages exist')
        for package in self._located_packages:
            if not os.path.isfile(package.path):
                raise Exception('Cannot find package %s at %s' % (package.name, package.path))

    def _check_package_locations_unique(self):
        logging.info('checking that package locations are unique')
        packages = set()
        for located_package in self._located_packages:
            package = located_package.package
            if package in packages:
                raise Exception('Multiple locations for package %s' % (package,))
            packages.add(package)

    def _check_package_fingerprints_valid(self):
        logging.info('checking that package fingerprints are valid')
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
        logging.info('checking that package fingerprints are unique')
        packages = set()
        for fingerprinted_package in self._fingerprinted_packages:
            package = fingerprinted_package.package
            if package in packages:
                raise Exception('Multiple fingerprints for package %s' % package)
            packages.add(package)

    def _check_upgrades_exist(self):
        logging.info('checking that upgraded packages exists')
        located = set()
        for located_package in self._located_packages:
            located.add(located_package.package)
        for group_package in self._package_upgrades:
            package = group_package.package
            if package not in located:
                raise Exception('Cannot locate upgraded package %s' % (package,))

    def _check_upgrades_valid(self):
        logging.info('checking that upgrades only upgrade builting packages')
        package_keys = set()
        for package in self._builtin_packages:
            package_keys.add((package.name, package.architecture))
        for group_package in self._package_upgrades:
            key = (group_package.name, group_package.architecture)
            if key not in package_keys:
                raise Exception('upgrade %s is not for a builtin package' % group_package)

    def _check_upgrades_unique(self):
        logging.info('checking that upgraded packages are unique per node')
        all_upgrades = set()
        for group_package in self._package_upgrades:
            key = (group_package.group, group_package.name, group_package.architecture)
            if key in all_upgrades:
                raise Exception('multiple upgrades to package %s for the same group %s' % (group_package.name, group_package.group))

    def _check_upgrades_newer(self):
        # TODO: Parse and compare versions
        pass
