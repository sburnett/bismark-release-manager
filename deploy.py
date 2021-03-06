from collections import defaultdict, namedtuple
import glob
import gzip
import logging
import os
import shutil
import StringIO
import stat
import subprocess
import tempfile

import common
import opkg
import release as bismark_release

_NodePackage = namedtuple('NodePackage',
                          ['node', 'name', 'version', 'architecture'])


class NodePackage(_NodePackage):

    @property
    def package(self):
        return bismark_release.Package(self.name, self.version, self.architecture)


def deploy(releases_root,
           destination,
           signing_key,
           releases,
           experiments,
           node_groups):
    deployment_path = tempfile.mkdtemp(prefix='bismark-downloads-staging-')
    logging.info('staging deployment in %s', deployment_path)

    # Fix permissons of the deployment path. mkdtemp gives 700 permissions,
    # and rsync will copy those permissions to the Web server, so we end
    # up with permission denied errors unless we fix permissions here.
    user_perms = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    group_perms = stat.S_IRGRP | stat.S_IXGRP
    other_perms = stat.S_IROTH | stat.S_IXOTH
    os.chmod(deployment_path, user_perms | group_perms | other_perms)

    for release in releases:
        _deploy_packages(release, deployment_path)
        _deploy_images(release, deployment_path)
        _deploy_builtin_packages(release, deployment_path)
        _deploy_extra_packages(release, deployment_path)
        _deploy_upgrades(release, node_groups, deployment_path)
        _deploy_experiment_packages(release,
                                    experiments,
                                    node_groups,
                                    deployment_path)
        _deploy_experiment_configurations(release,
                                          experiments,
                                          node_groups,
                                          deployment_path)
    _make_dummy_directories(deployment_path)
    _deploy_dummy_experiment_configurations(deployment_path)
    _deploy_packages_gz(deployment_path)
    _deploy_packages_sig(deployment_path, signing_key)
    _deploy_upgradable_sentinels(deployment_path)
    _deploy_static(releases_root, deployment_path)

    print 'The following files differ at the destination:'
    diff_success = _diff_from_destination(deployment_path, destination)

    if diff_success:
        deploy_response = raw_input('\nDeploy to %s? (y/N) ' % (destination,))
        if deploy_response == 'y':
            print 'Deploying from %s to %s' % (deployment_path, destination)
            _copy_to_destination(deployment_path, destination)
        else:
            print 'Skipping deployment'

    clean_response = raw_input(
        '\nDelete staging directory %s? (Y/n) ' % (deployment_path,))
    if clean_response != 'n':
        print 'Removing staging directory %s' % (deployment_path,)
        shutil.rmtree(deployment_path)
    else:
        print 'Staging directory %s left intact' % (deployment_path,)


def _deploy_packages(release, deployment_path):
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


def _deploy_images(release, deployment_path):
    images_path = release.images_path
    for image in release.images:
        destination_dir = os.path.join(deployment_path,
                                       release.name,
                                       image.architecture)
        common.makedirs(destination_dir)
        shutil.copy2(os.path.join(images_path, image.name), destination_dir)


def _deployment_package_paths(release, deployment_path):
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


def _deploy_builtin_packages(release, deployment_path):
    package_paths = _deployment_package_paths(release, deployment_path)
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


def _deploy_extra_packages(release, deployment_path):
    package_paths = _deployment_package_paths(release, deployment_path)
    for package in release.extra_packages:
        source = package_paths[package]
        architectures = release.normalize_architecture(package.architecture)
        for architecture in architectures:
            link_dir = os.path.join(deployment_path,
                                    release.name,
                                    architecture,
                                    'extra-packages')
            common.makedirs(link_dir)
            link_name = os.path.join(link_dir, os.path.basename(source))
            relative_source = os.path.relpath(source, link_dir)
            os.symlink(relative_source, link_name)


def _resolve_groups_to_nodes(node_groups, group_packages):
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
            raise Exception('Conflicting package versions for a node: %s' % (key,))
        packages_per_node.add(key)

    return node_packages


def _normalize_default_packages(node_packages, nodes):
    logging.info('normalizing packages')
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


def _symlink_packages(release, packages, subdirectory, deployment_path):
    package_paths = _deployment_package_paths(release, deployment_path)
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


def _deploy_upgrades(release, node_groups, deployment_path):
    resolved_upgrades = _resolve_groups_to_nodes(
        node_groups,
        release.package_upgrades)
    nodes = set()
    for node_package in resolved_upgrades:
        nodes.add(node_package.node)
    upgraded_packages = _normalize_default_packages(resolved_upgrades, nodes)
    _symlink_packages(release,
                      upgraded_packages,
                      'updates-device',
                      deployment_path)


def _deploy_experiment_packages(release,
                                experiments,
                                node_groups,
                                deployment_path):

    all_group_packages = set()
    for name, experiment in experiments.iteritems():
        for group_package in experiment.packages:
            if group_package.release != release.name:
                continue
            all_group_packages.add(group_package)
    node_packages = _resolve_groups_to_nodes(node_groups, all_group_packages)
    nodes = set()
    for node_package in node_packages:
        nodes.add(node_package.node)
    for _, experiment in experiments.iteritems():
        for group in experiment.header_groups:
            nodes.update(node_groups.resolve_to_nodes(group))
    normalized_packages = _normalize_default_packages(node_packages, nodes)
    _symlink_packages(release,
                      normalized_packages,
                      'experiments-device',
                      deployment_path)


def _normalize_default_experiments(node_dicts):
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


def _bool_to_string(b):
    if b:
        return '1'
    else:
        return '0'


def _normalized_configuration_headers(experiments, node_groups):
    group_configuration_headers = defaultdict(dict)
    for name, experiment in experiments.iteritems():
        for group in experiment.header_groups:
            s = StringIO.StringIO()
            print >>s, "config 'experiment' '%s'" % experiment.name
            print >>s, "    option 'display_name' '%s'" % experiment.display_name
            print >>s, "    option 'description' '%s'" % experiment.description
            for conflict in experiment.conflicts:
                print >>s, "    list 'conflicts' '%s'" % conflict
            required = _bool_to_string(experiment.is_required(group))
            print >>s, "    option 'required' '%s'" % required
            revoked = _bool_to_string(experiment.is_revoked(group))
            print >>s, "    option 'revoked' '%s'" % revoked
            installed = _bool_to_string(
                experiment.is_installed_by_default(group))
            print >>s, "    option 'installed' '%s'" % installed
            group_configuration_headers[group][name] = s.getvalue()

    node_configuration_headers = defaultdict(dict)
    for group, headers in group_configuration_headers.items():
        for node in node_groups.resolve_to_nodes(group):
            for experiment, header in headers.items():
                if (experiment in node_configuration_headers[node] and
                        node_configuration_headers[node][experiment] != header):
                    raise Exception('conflicting experiment defintions')
                node_configuration_headers[node][experiment] = header
    return _normalize_default_experiments(node_configuration_headers)


def _normalized_configuration_bodies(release, experiments, node_groups):
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
                        if key in bodies[node] and bodies[node][key] != package.version:
                            raise Exception(
                                    'conflicting versions for package in experiment: %s' % (key,))
                        bodies[node][key] = package.version
    return _normalize_default_experiments(bodies)


def _deploy_experiment_configurations(release,
                                      experiments,
                                      node_groups,
                                      deployment_path):
    normalized_headers = _normalized_configuration_headers(
        experiments, node_groups)
    normalized_bodies = _normalized_configuration_bodies(
        release, experiments, node_groups)

    all_nodes = set()
    all_nodes.update(normalized_headers.keys())
    all_nodes.update(normalized_bodies.keys())

    configurations = defaultdict(dict)
    for node in all_nodes:
        if node in normalized_bodies:
            packages = normalized_bodies[node]
        elif 'default' in normalized_bodies:
            packages = normalized_bodies['default']
        else:
            continue
        for architecture, experiment, name in sorted(packages):
            if experiment not in configurations[architecture, node]:
                if node in normalized_headers and experiment in normalized_headers[node]:
                    headers = normalized_headers[node][experiment]
                else:
                    headers = normalized_headers['default'][experiment]
                configurations[architecture, node][experiment] = headers
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


def _make_dummy_directories(deployment_path):
    patterns = [
        '*/*',
    ]
    for pattern in patterns:
        full_pattern = os.path.join(deployment_path, pattern)
        for dirname in glob.iglob(full_pattern):
            if os.path.dirname(dirname) == 'packages':
                continue
            common.makedirs(os.path.join(dirname, 'experiments'))
            common.makedirs(os.path.join(dirname, 'updates'))


def _deploy_dummy_experiment_configurations(deployment_path):
    patterns = [
        '*/*/experiments',
    ]
    for pattern in patterns:
        full_pattern = os.path.join(deployment_path, pattern)
        for dirname in glob.iglob(full_pattern):
            experiments_filename = os.path.join(dirname, 'Experiments')
            with open(experiments_filename, 'w') as handle:
                print >>handle


def _deploy_packages_gz(deployment_path):
    patterns = [
        '*/*/experiments',
        '*/*/experiments-device/*',
        '*/*/extra-packages',
        '*/*/packages',
        '*/*/updates',
        '*/*/updates-device/*',
    ]
    for pattern in patterns:
        full_pattern = os.path.join(deployment_path, pattern)
        for dirname in glob.iglob(full_pattern):
            package_indices = []
            for filename in sorted(glob.glob(os.path.join(dirname, '*.ipk'))):
                package_index = opkg.generate_package_index(filename)
                package_indices.append(package_index)
            index_contents = '\n'.join(package_indices)
            index_filename = os.path.join(dirname, 'Packages.gz')
            handle = gzip.GzipFile(index_filename, 'wb', mtime=0)
            handle.write(index_contents)
            handle.close()


def _deploy_packages_sig(deployment_path, signing_key):
    signing_key_path = os.path.expanduser(signing_key)
    if not os.path.isfile(signing_key_path):
        raise Exception('Cannot find signing key %r' % (signing_key_path,))

    if stat.S_IMODE(os.stat(signing_key_path).st_mode) != 0400:
        raise Exception('For security, %r must have 0400 permissions' % (
            signing_key_path,))

    patterns = [
        '*/*/experiments',
        '*/*/experiments-device/*',
        '*/*/extra-packages',
        '*/*/packages',
        '*/*/updates',
        '*/*/updates-device/*',
    ]
    for pattern in patterns:
        full_pattern = os.path.join(deployment_path, pattern)
        for dirname in glob.iglob(full_pattern):
            packages_gz_filename = os.path.join(dirname, 'Packages.gz')
            if not os.path.isfile(packages_gz_filename):
                continue
            packages_sig_filename = os.path.join(dirname, 'Packages.sig')
            command = 'openssl smime -in %s -sign -signer %s -binary -outform PEM -out %s' % (
                packages_gz_filename, signing_key_path, packages_sig_filename)
            logging.info('Going to run: %s', command)
            return_code = subprocess.call(command, shell=True)
            if return_code != 0:
                logging.error('openssl smime exited with error code %s',
                              return_code)
                raise Exception('Error signing Packages.gz')


def _deploy_upgradable_sentinels(deployment_path):
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


def _deploy_static(releases_root, deployment_path):
    static_pattern = os.path.join(releases_root, 'static', '*')
    for filename in glob.iglob(static_pattern):
        if os.path.isdir(filename):
            continue
        if os.path.islink(filename):
            destination = os.readlink(filename)
            source = os.path.join(deployment_path, os.path.basename(filename))
            os.symlink(destination, source)
            continue
        shutil.copy2(filename, deployment_path)


def _diff_from_destination(deployment_path, destination):
    command = 'rsync -n -icvlrz --exclude=Packages.sig --delete %s/ %s' % (
        deployment_path, destination)
    logging.info('Going to run: %s', command)
    return_code = subprocess.call(command, shell=True)
    if return_code != 0:
        print 'rsync exited with error code %d' % return_code
        return False
    return True


def _copy_to_destination(deployment_path, destination):
    command = 'rsync -cvaz --delete %s/ %s' % (deployment_path, destination)
    logging.info('Going to run: %s', command)
    return_code = subprocess.call(command, shell=True)
    if return_code != 0:
        print 'rsync exited with error code %d' % return_code
