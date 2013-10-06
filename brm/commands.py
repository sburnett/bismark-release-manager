import os

import tree

def new_release(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    openwrt_build_root = os.path.expanduser(args.buildroot)
    releases_tree.new_release(args.name, openwrt_build_root)

def add_packages(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    releases_tree.add_packages(args.release, args.ipk)

def list_architectures(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    for package in sorted(releases_tree.architectures(args.release)):
        print ' '.join(package)

def list_releases(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    for release_name in releases_tree.releases:
        print release_name

def list_builtin_packages(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    for package in sorted(releases_tree.builtin_packages(args.release)):
        if (args.architecture is not None and
                package.architecture != args.architecture):
            continue
        print ' '.join(package)

def new_group(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    releases_tree.new_group(args.name)
    releases_tree.add_to_group(args.name, args.node)

def delete_group(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    releases_tree.delete_group(args.name)

def add_to_group(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    releases_tree.add_to_group(args.group, args.node)

def remove_from_group(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    releases_tree.remove_from_group(args.group, args.node)

def list_groups(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    for group in releases_tree.groups():
        print group

def list_group(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    for node in releases_tree.nodes_in_group(args.name):
        print node

def upgrade_package(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    releases_tree.upgrade_package(args.release, args.package, args.version, args.architecture, args.group)

def list_upgrades(args):
    releases_root = os.path.expanduser(args.root)
    releases_tree = tree.BismarkReleasesTree(releases_root)
    upgrades = releases_tree.upgrades(args.release, args.architecture, args.group, args.package)
    for upgrade in sorted(upgrades):
        print ' '.join(upgrade)
