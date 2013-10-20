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

    def builtin_packages(self, release_name):
        logging.info('Getting builtin packages for release %r', release_name)
        bismark_release = release.open_bismark_release(
                self._release_path(release_name))
        return bismark_release.builtin_packages

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
                        group_names):
        logging.info('Upgrading package %r to version %r '
                     'on architecture %r for release %r',
                     name,
                     version,
                     architecture,
                     release_name)
        bismark_release = release.open_bismark_release(
                self._release_path(release_name))
        node_groups = groups.NodeGroups(self._groups_path())
        for group_name in group_names:
            if group_name in node_groups:
                logging.info('Upgrading group %r', group_name)
                for node in node_groups[group_name]:
                    logging.info('Upgrading node %r in group %r',
                                 node,
                                 group_name)
                    bismark_release.upgrade_package(node,
                                                    name,
                                                    version,
                                                    architecture)
            else:
                logging.info('Upgrading node %r', group_name)
                bismark_release.upgrade_package(group_name,
                                                name,
                                                version,
                                                architecture)
        bismark_release.save()

    def upgrades(self, release_name, architecture, group_name, packages):
        logging.info('Getting upgrades for architecture %r and release %r',
                     architecture,
                     release_name)
        bismark_release = release.open_bismark_release(
                self._release_path(release_name))
        node_groups = groups.NodeGroups(self._groups_path())
        if group_name in node_groups:
            logging.info('Getting upgrades for group %r', group_name)
            nodes = node_groups[group_name]
        else:
            logging.info('Getting upgrades for single node %r', group_name)
            nodes = set([group_name])
        upgrades = set()
        if packages == []:
            logging.info('Getting upgrades for all builtin packages')
            for package in bismark_release.builtin_packages:
                packages.append(package.name)
        for package in packages:
            logging.info('Getting upgrades for package %r', package)
            for node in nodes:
                node_package = bismark_release.get_upgrade(
                        node,
                        package,
                        architecture)
                if node_package is None:
                    logging.info('No upgrades for package %r on node %r '
                                 'and architecture %r',
                                 package,
                                 node,
                                 architecture)
                    continue
                upgrades.add(node_package)
        return upgrades

    def new_experiment(self, name, display_name, description):
        logging.info('Creating new experiment %s', name)
        self._experiments.new_experiment(name, display_name, description)
        self._experiments.write_to_files()

    def add_to_experiment(self, experiment, groups, *rest):
        logging.info('Adding groups to experiment %s', experiment)
        for group in groups:
            self._experiments[experiment].add_package(group, *rest)
        self._experiments.write_to_files()

    def remove_from_experiment(self, experiment, groups, *rest):
        logging.info('Removing groups from experiment %s', experiment)
        for group in groups:
            self._experiments[experiment].remove_package(group, *rest)
        self._experiments.write_to_files()

    def set_experiment_required(self, experiment, required, groups):
        logging.info('Set required to %r for experiment %r',
                     required,
                     experiment)
        for group in groups:
            self._experiments[experiment].set_required(group, required)
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

    def commit(self):
        os.chdir(self._root)
        if not os.path.isdir('.git'):
            subprocess.check_call(['git', 'init'])
        patterns = [
                'groups/*',
                'releases/*/architectures',
                'releases/*/builtin-packages',
                'releases/*/fingerprinted-images',
                'releases/*/fingerprinted-packages',
                'releases/*/package-upgrades',
                ]
        for pattern in patterns:
            for filename in glob.iglob(pattern):
                subprocess.check_call(['git', 'add', filename])
        if subprocess.call(['git', 'diff', '--exit-code']) != 0:
            subprocess.check_call(['git', 'commit', '-a'])

    def deploy(self, destination):
        self.check_constraints()
        node_groups = groups.NodeGroups(self._groups_path())
        releases = []
        for release_name in self.releases:
            release_path = self._release_path(release_name)
            bismark_release = release.open_bismark_release(release_path)
            releases.append(bismark_release)
        deploy.deploy(destination,
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

        self._experiments.check_constraints()

    def _release_path(self, release_name):
        return os.path.join(self._root, 'releases', release_name)

    def _groups_path(self):
        return os.path.join(self._root, 'groups')

    def _experiments_path(self):
        return os.path.join(self._root, 'experiments')
