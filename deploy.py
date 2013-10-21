from collections import defaultdict, namedtuple
import glob
import gzip
import logging
import os
import shutil
import StringIO

import common
import opkg
import release as bismark_release

_NodePackage = namedtuple('NodePackage',
                          ['node', 'name', 'version', 'architecture'])


class NodePackage(_NodePackage):

    @property
    def package(self):
        return bismark_release.Package(self.name, self.version, self.architecture)


def deploy(deployment_path, releases, experiments, node_groups):
    common.makedirs(deployment_path)

    for release in releases:
        deploy_packages(release, deployment_path)
        deploy_images(release, deployment_path)
        deploy_builtin_packages(release, deployment_path)
        deploy_extra_packages(release, deployment_path)
        deploy_upgrades(release, node_groups, deployment_path)
        deploy_experiment_packages(release,
                                   experiments,
                                   node_groups,
                                   deployment_path)
        deploy_experiment_configurations(release,
                                         experiments,
                                         node_groups,
                                         deployment_path)
    deploy_packages_gz(deployment_path)
    deploy_upgradable_sentinels(deployment_path)


def deploy_packages(release, deployment_path):
    packages_path = release.packages_path
    for package in release.packages:
        destination = os.path.join(deployment_path,
                                   'packages',
                                   release.name,
                                   package.architecture)
        common.makedirs(destination)
        destination_path = os.path.join(destination, package.filename)
        source_filename = os.path.join(packages_path, '%s.ipk' % package.sha1)
        shutil.copy2(source_filename, destination_path)


def deploy_images(release, deployment_path):
    for located_image in release.images:
        destination_dir = os.path.join(deployment_path,
                                       release.name,
                                       located_image.architecture)
        common.makedirs(destination_dir)
        shutil.copy2(located_image.path, destination_dir)


def deployment_package_paths(release, deployment_path):
    logging.info('locating package in deployed path')
    package_paths = dict()
    for package in release.packages:
        package_path = os.path.join(
            deployment_path,
            'packages',
            release.name,
            package.architecture,
            package.filename)
        package_paths[package.package] = package_path
    return package_paths


def deploy_builtin_packages(release, deployment_path):
    package_paths = deployment_package_paths(release, deployment_path)
    for package in release.builtin_packages:
        source = package_paths[package]
        architectures = release.normalize_architecture(package.architecture)
        for architecture in architectures:
            link_dir = os.path.join(deployment_path,
                                    release.name,
                                    architecture,
                                    'packages')
            common.makedirs(link_dir)
            link_name = os.path.join(link_dir, os.path.basename(source))
            relative_source = os.path.relpath(source, link_dir)
            os.symlink(relative_source, link_name)


def deploy_extra_packages(release, deployment_path):
    package_paths = deployment_package_paths(release, deployment_path)
    for package in release.extra_packages:
        source = package_paths[package]
        architectures = release.normalize_architecture(package.architecture)
        for architecture in architectures:
            link_dir = os.path.join(deployment_path,
                                    release.name,
                                    architecture,
                                    'packages')
            common.makedirs(link_dir)
            link_name = os.path.join(link_dir, os.path.basename(source))
            relative_source = os.path.relpath(source, link_dir)
            os.symlink(relative_source, link_name)


def resolve_groups_to_nodes(node_groups, group_packages):
    logging.info('resolving groups to nodes')
    node_packages = set()
    for group_package in group_packages:
        for node in node_groups.resolve_to_nodes(group_package.group):
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


def normalize_default_packages(node_packages):
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


def symlink_packages(release, packages, subdirectory, deployment_path):
    package_paths = deployment_package_paths(release, deployment_path)
    for package in packages:
        source = package_paths[package.package]
        architectures = release.normalize_architecture(package.architecture)
        for architecture in architectures:
            link_dir = os.path.join(deployment_path,
                                    release.name,
                                    architecture,
                                    subdirectory,
                                    package.node)
            common.makedirs(link_dir)
            link_name = os.path.join(link_dir, os.path.basename(source))
            relative_source = os.path.relpath(source, link_dir)
            os.symlink(relative_source, link_name)


def deploy_upgrades(release, node_groups, deployment_path):
    resolved_upgrades = resolve_groups_to_nodes(
        node_groups,
        release.package_upgrades)
    upgraded_packages = normalize_default_packages(resolved_upgrades)
    symlink_packages(release,
                     upgraded_packages,
                     'updates-device',
                     deployment_path)


def deploy_experiment_packages(release,
                               experiments,
                               node_groups,
                               deployment_path):

    all_group_packages = set()
    for name, experiment in experiments.iteritems():
        for group_package in experiment.packages:
            if group_package.release != release.name:
                continue
            all_group_packages.add(group_package)
    node_packages = resolve_groups_to_nodes(node_groups, all_group_packages)
    normalized_packages = normalize_default_packages(node_packages)
    symlink_packages(release,
                     normalized_packages,
                     'experiments-device',
                     deployment_path)


def normalize_default_experiments(node_dicts):
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


def bool_to_string(b):
    if b:
        return '1'
    else:
        return '0'


def deploy_experiment_configurations(release,
                                     experiments,
                                     node_groups,
                                     deployment_path):
    group_configuration_headers = defaultdict(dict)
    for name, experiment in experiments.iteritems():
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
            installed = bool_to_string(
                experiment.is_installed_by_default(group))
            print >>s, "    option 'installed' '%s'" % installed
            group_configuration_headers[group][name] = s.getvalue()

    node_configuration_headers = defaultdict(dict)
    for group, headers in group_configuration_headers.items():
        for node in node_groups.resolve_to_nodes(group):
            for experiment, header in headers.items():
                if experiment in node_configuration_headers[node]:
                    raise Exception('conflicting experiment defintions')
                node_configuration_headers[node][experiment] = header
    normalized_headers = normalize_default_experiments(
        node_configuration_headers)

    group_experiment_packages = defaultdict(lambda: defaultdict(set))
    for name, experiment in experiments.iteritems():
        for group_package in experiment.packages:
            if group_package.release != release.name:
                continue
            group_experiment_packages[
                group_package.group][name].add(group_package)

    bodies = defaultdict(dict)
    for group, experiment_packages in group_experiment_packages.items():
        for node in node_groups.resolve_to_nodes(group):
            for experiment, packages in experiment_packages.items():
                for package in packages:
                    architectures = release.normalize_architecture(
                        package.architecture)
                    for architecture in architectures:
                        key = architecture, experiment, package.name
                        if key in bodies[node]:
                            raise Exception(
                                'conflicting packages for experiment')
                        bodies[node][key] = package
    normalized_bodies = normalize_default_experiments(bodies)

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
                                release.name,
                                architecture,
                                'experiments-device',
                                node,
                                'Experiments')
        common.makedirs(os.path.dirname(filename))
        with open(filename, 'w') as handle:
            for name, configuration in sorted(experiments.items()):
                handle.write(configuration)
                print >>handle, ''


def deploy_packages_gz(deployment_path):
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


def deploy_upgradable_sentinels(deployment_path):
    patterns = [
        '*/*/updates-device/*',
        '*/*/experiments-device/*',
    ]
    for pattern in patterns:
        full_pattern = os.path.join(deployment_path, pattern)
        for dirname in glob.iglob(full_pattern):
            if not os.path.isdir(dirname):
                continue
            with open(os.path.join(dirname, 'Upgradable'), 'w'):
                pass
