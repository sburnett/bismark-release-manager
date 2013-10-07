import errno
import glob
import logging
import os
import subprocess

import groups
import openwrt
import release

class BismarkReleasesTree(object):
    def __init__(self, root):
        self._root = root

        try:
            os.makedirs(root)
        except OSError as err:
            if err.errno == errno.EEXIST:
                logging.info('Releases tree %r already exists', root)
            else:
                raise

    def new_release(self, name, build_root):
        release_path = self._release_path(name)
        if os.path.isdir(release_path):
            raise Exception('Release %r already exists' % name)

        openwrt_build = openwrt.BuildTree(build_root)
        bismark_release = release.NewBismarkRelease(
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
        bismark_release = release.BismarkRelease(
                self._release_path(release_name))
        return bismark_release.builtin_packages

    def architectures(self, release_name):
        logging.info('Getting architectures for release %r', release_name)
        bismark_release = release.BismarkRelease(
                self._release_path(release_name))
        return bismark_release.architectures

    def packages(self, release_name):
        logging.info('Getting packages for release %r', release_name)
        bismark_release = release.BismarkRelease(
                self._release_path(release_name))
        return bismark_release.packages

    def add_packages(self, release_name, filenames):
        bismark_release = release.BismarkRelease(
                self._release_path(release_name))
        for filename in filenames:
            logging.info('Add package %r to release %r',
                         filename,
                         release_name)
            bismark_release.add_package(filename)
        bismark_release.save()

    def groups(self):
        logging.info('Getting groups')
        node_groups = groups.NodeGroups(self._groups_path())
        return node_groups.groups

    def nodes_in_group(self, name):
        logging.info('Getting nodes for group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        return node_groups.nodes_in_group(name)

    def new_group(self, name):
        logging.info('Creating group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        node_groups.new_group(name)
        node_groups.write_to_files()

    def delete_group(self, name):
        logging.info('Deleting group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        node_groups.delete_group(name)
        node_groups.write_to_files()

    def add_to_group(self, name, nodes):
        logging.info('Adding to group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        for node in nodes:
            logging.info('Adding node %r to group %r', node, name)
            node_groups.add_to_group(name, node)
        node_groups.write_to_files()

    def remove_from_group(self, name, nodes):
        logging.info('Removing from group %r', name)
        node_groups = groups.NodeGroups(self._groups_path())
        for node in nodes:
            logging.info('Removing node %r from group %r', node, name)
            node_groups.remove_from_group(name, node)
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
        bismark_release = release.BismarkRelease(
                self._release_path(release_name))
        node_groups = groups.NodeGroups(self._groups_path())
        for group_name in group_names:
            if group_name in node_groups.groups:
                logging.info('Upgrading group %r', group_name)
                for node in node_groups.nodes_in_group(group_name):
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
        bismark_release = release.BismarkRelease(
                self._release_path(release_name))
        node_groups = groups.NodeGroups(self._groups_path())
        if group_name in node_groups.groups:
            logging.info('Getting upgrades for group %r', group_name)
            nodes = node_groups.nodes_in_group(group_name)
        else:
            logging.info('Getting upgrades for single node %r', group_name)
            nodes = [group_name]
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
        for release_name in self.releases:
            release_path = self._release_path(release_name)
            bismark_release = release.BismarkRelease(release_path)
            bismark_release.check_constraints()

        for release_name in self.releases:
            release_path = self._release_path(release_name)
            bismark_release = release.BismarkRelease(release_path)

            bismark_release.deploy_packages(destination)
            bismark_release.deploy_images(destination)
            bismark_release.deploy_builtin_packages(destination)
            node_groups = groups.NodeGroups(self._groups_path())
            bismark_release.deploy_upgrades(node_groups, destination)

    def _release_path(self, release_name):
        return os.path.join(self._root, 'releases', release_name)

    def _groups_path(self):
        return os.path.join(self._root, 'groups')
