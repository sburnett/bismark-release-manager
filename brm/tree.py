import errno
import glob
import logging
import os

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
                logging.info('Releases tree %s already exists', root)
            else:
                raise

    def new_release(self, name, build_root):
        release_path = self._release_path(name)
        if os.path.isdir(release_path):
            raise Exception('Release "%s" already exists' % name)

        openwrt_build = openwrt.BuildTree(build_root)
        bismark_release = release.NewBismarkRelease(release_path, openwrt_build)
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
        bismark_release = release.BismarkRelease(self._release_path(release_name))
        return bismark_release.builtin_packages

    def architectures(self, release_name):
        bismark_release = release.BismarkRelease(self._release_path(release_name))
        return bismark_release.architectures

    def add_packages(self, release_name, filenames):
        bismark_release = release.BismarkRelease(self._release_path(release_name))
        for filename in filenames:
            bismark_release.add_package(filename)
        bismark_release.save()

    def groups(self):
        node_groups = groups.NodeGroups(self._groups_path())
        return node_groups.groups

    def nodes_in_group(self, name):
        node_groups = groups.NodeGroups(self._groups_path())
        return node_groups.nodes_in_group(name)

    def new_group(self, name):
        node_groups = groups.NodeGroups(self._groups_path())
        node_groups.new_group(name)
        node_groups.write_to_files()

    def delete_group(self, name):
        node_groups = groups.NodeGroups(self._groups_path())
        node_groups.delete_group(name)
        node_groups.write_to_files()

    def add_to_group(self, name, nodes):
        node_groups = groups.NodeGroups(self._groups_path())
        for node in nodes:
            node_groups.add_to_group(name, node)
        node_groups.write_to_files()

    def remove_from_group(self, name, nodes):
        node_groups = groups.NodeGroups(self._groups_path())
        for node in nodes:
            node_groups.remove_from_group(name, node)
        node_groups.write_to_files()

    def upgrade_package(self, release_name, name, version, architecture, group_names):
        bismark_release = release.BismarkRelease(self._release_path(release_name))
        node_groups = groups.NodeGroups(self._groups_path())
        for group_name in group_names:
            if group_name in node_groups.groups:
                for node in node_groups.nodes_in_group(group_name):
                    bismark_release.upgrade_package(node, name, version, architecture)
            else:
                bismark_release.upgrade_package(group_name, name, version, architecture)
        bismark_release.save()

    def upgrades(self, release_name, architecture, group_name, packages):
        bismark_release = release.BismarkRelease(self._release_path(release_name))
        node_groups = groups.NodeGroups(self._groups_path())
        if group_name in node_groups.groups:
            nodes = node_groups.nodes_in_group(group_name)
        else:
            nodes = [group_name]
        upgrades = set()
        if packages == []:
            for package in bismark_release.builtin_packages:
                packages.append(package.name)
        for package in packages:
            for node in nodes:
                node_package = bismark_release.get_upgrade(node, package, architecture)
                if node_package is None:
                    continue
                upgrades.add(node_package)
        return upgrades

    def _release_path(self, release_name):
        return os.path.join(self._root, 'releases', release_name)

    def _groups_path(self):
        return os.path.join(self._root, 'groups')
