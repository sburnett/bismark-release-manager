import glob
import logging
import os
import subprocess

import common
import deploy
import experiments
import groups
import openwrt
import release


class BismarkReleasesTree(object):

    def __init__(self, root):
        self._root = root
        common.makedirs(root)

        self._experiments = experiments.Experiments(self._experiments_path())

    def new_release(self, name, build_root):
        release_path = self._release_path(name)
        if os.path.isdir(release_path):
            raise Exception('Release %r already exists' % name)

        openwrt_build = openwrt.BuildTree(build_root)
        bismark_release = release.new_bismark_release(
            release_path,
            openwrt_build)
        bismark_release.save()

    @property
    def releases(self):
        releases = set()
        pattern = os.path.join(self._root, 'releases', '*')
        for filename in glob.iglob(pattern):
            if not os.path.isdir(filename):
                continue
            releases.add(os.path.basename(filename))
        return releases

    def normalize_release_name(self, release_name):
        if release_name == 'all':
            return self.releases
        else:
            return set([release_name])

    def builtin_packages(self, release_name):
        logging.info('Getting builtin packages for release %r', release_name)
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        return bismark_release.builtin_packages

    def extra_packages(self, release_name):
        logging.info('Getting extra packages for release %r', release_name)
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        return bismark_release.extra_packages

    def architectures(self, release_name):
        logging.info('Getting architectures for release %r', release_name)
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        return bismark_release.architectures

    def packages(self, release_name):
        logging.info('Getting packages for release %r', release_name)
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        return bismark_release.packages

    @property
    def experiments(self):
        logging.info('Getting all experiments %r')
        return self._experiments

    def experiment_packages(self, experiment_name):
        logging.info('Getting packages for experiment %r', experiment_name)
        return self._experiments[experiment_name].packages

    def add_packages(self, release_name, filenames):
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        for filename in filenames:
            logging.info('Add package %r to release %r',
                         filename,
                         release_name)
            bismark_release.add_package(filename)
        bismark_release.save()

    def add_extra_package(self, release_name, *rest):
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        bismark_release.add_extra_package(*rest)
        bismark_release.save()

    def remove_extra_package(self, release_name, *rest):
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        bismark_release.remove_extra_package(*rest)
        bismark_release.save()

    @property
    def groups(self):
        logging.info('Getting groups')
        return groups.NodeGroups(self._groups_path())

    def nodes_in_group(self, name):
        logging.info('Getting nodes for group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        return node_groups[name]

    def new_group(self, name):
        logging.info('Creating group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        node_groups.new_group(name)
        node_groups.write_to_files()

    def copy_group(self, name, new_name):
        logging.info('Creating group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        node_groups.new_group(new_name)
        for node in node_groups[name]:
            node_groups[new_name].add(node)
        node_groups.write_to_files()

    def delete_group(self, name):
        logging.info('Deleting group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        del node_groups[name]
        node_groups.write_to_files()

    def add_to_group(self, name, nodes):
        logging.info('Adding to group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        for node in nodes:
            logging.info('Adding node %r to group %r', node, name)
            node_groups[name].add(node)
        node_groups.write_to_files()

    def remove_from_group(self, name, nodes):
        logging.info('Removing from group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        for node in nodes:
            logging.info('Removing node %r from group %r', node, name)
            node_groups[name].remove(node)
        node_groups.write_to_files()

    def upgrade_package(self,
                        release_name,
                        name,
                        version,
                        architecture,
                        group_name):
        logging.info('Upgrading package %r to version %r '
                     'on architecture %r for release %r',
                     name,
                     version,
                     architecture,
                     release_name)
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        bismark_release.upgrade_package(group_name,
                                        name,
                                        version,
                                        architecture)
        bismark_release.save()

    def upgrades(self, release_name):
        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        return bismark_release.package_upgrades

    def new_experiment(self, name, display_name, description):
        logging.info('Creating new experiment %s', name)
        self._experiments.new_experiment(name, display_name, description)
        self._experiments.write_to_files()

    def add_to_experiment(self, experiment, group, release_name, *rest):
        logging.info('Adding group to experiment %s', experiment)

        bismark_release = release.open_bismark_release(
            self._release_path(release_name))
        package = release.Package(*rest)
        located_package = bismark_release.locate_package(package)
        if located_package is None:
            raise Exception('Cannot find package %r' % (package,))

        self._experiments[experiment].add_package(
            group, release_name, *rest)
        self._experiments.write_to_files()

    def remove_from_experiment(self, experiment, group, *rest):
        logging.info('Removing group from experiment %s', experiment)
        self._experiments[experiment].remove_package(group, *rest)
        self._experiments.write_to_files()

    def set_experiment_required(self, experiment, required, groups):
        logging.info('Set required to %r for experiment %r',
                     required,
                     experiment)
        for group in groups:
            self._experiments[experiment].set_required(group, required)
        self._experiments.write_to_files()

    def set_experiment_revoked(self, experiment, revoked, groups):
        logging.info('Set revoked to %r for experiment %r',
                     revoked,
                     experiment)
        for group in groups:
            self._experiments[experiment].set_revoked(group, revoked)
        self._experiments.write_to_files()

    def set_experiment_installed_by_default(self,
                                            experiment,
                                            installed,
                                            groups):
        logging.info('Set install by default to %r for experiment %r',
                     installed,
                     experiment)
        for group in groups:
            self._experiments[experiment].set_installed_by_default(group,
                                                                   installed)
        self._experiments.write_to_files()

    def _stage_changes(self):
        os.chdir(self._root)
        if not os.path.isdir('.git'):
            subprocess.check_call(['git', 'init'])
        patterns = [
            'experiments/*/*',
            'groups/*',
            'releases/*/architectures',
            'releases/*/builtin-packages',
            'releases/*/extra-packages',
            'releases/*/fingerprinted-images',
            'releases/*/fingerprinted-packages',
            'releases/*/images/*',
            'releases/*/package-upgrades',
            'releases/*/packages/*',
            'static/*',
        ]
        for pattern in patterns:
            for filename in glob.iglob(pattern):
                subprocess.check_call(['git', 'add', filename])

    def commit(self):
        self._stage_changes()
        if subprocess.call(['git', 'diff', '--cached', '--exit-code']) != 0:
            subprocess.check_call(['git', 'commit', '-a'])

    def diff(self):
        self._stage_changes()
        subprocess.call(['git', 'diff', '--cached'])

    def deploy(self, destination, signing_key):
        self.check_constraints()
        node_groups = groups.NodeGroups(self._groups_path())
        releases = []
        for release_name in self.releases:
            release_path = self._release_path(release_name)
            bismark_release = release.open_bismark_release(release_path)
            releases.append(bismark_release)
        deploy.deploy(self._root,
                      destination,
                      signing_key,
                      releases,
                      self._experiments,
                      node_groups)

    def check_constraints(self):
        logging.info('Checking release constraints')
        for release_name in self.releases:
            logging.info('Checking constraints for release %r', release_name)
            release_path = self._release_path(release_name)
            bismark_release = release.open_bismark_release(release_path)
            bismark_release.check_constraints()

            logging.info('Checking if experiments include builtin packages')
            for builtin_package in bismark_release.builtin_packages:
                for name, experiment in self._experiments.iteritems():
                    for package in experiment.packages:
                        if package.name != builtin_package.name:
                            continue
                        if package.release != release_name:
                            continue
                        if (package.architecture != builtin_package.architecture
                                and builtin_package.architecture != 'all'
                                and package.architecture != 'all'):
                            continue
                        raise Exception(
                            'Experiment %r contains builtin package %r' % (
                                name, builtin_package.name))

            logging.info('Checking if experiments include extra packages')
            for extra_package in bismark_release.extra_packages:
                for name, experiment in self._experiments.iteritems():
                    for package in experiment.packages:
                        if package.name != extra_package.name:
                            continue
                        if package.release != release_name:
                            continue
                        if (package.architecture != extra_package.architecture
                                and extra_package.architecture != 'all'
                                and package.architecture != 'all'):
                            continue
                        raise Exception(
                            'Experiment %r contains "extra" package %r' % (
                                name, extra_package.name))

        self._experiments.check_constraints()

    def _release_path(self, release_name):
        return os.path.join(self._root, 'releases', release_name)

    def _groups_path(self):
        return os.path.join(self._root, 'groups')

    def _experiments_path(self):
        return os.path.join(self._root, 'experiments')
