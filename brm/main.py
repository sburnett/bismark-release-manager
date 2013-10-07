#!/usr/bin/env python2.7

import argparse
import logging
import os
import sys

import commands

def main():
    parser = argparse.ArgumentParser(description='Publish releases of BISmark images, packages, and experiments')
    parser.add_argument('--root', dest='root', action='store', default='~/bismark-releases', help='store release configuration in this directory')
    log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITITCAL']
    parser.add_argument('--loglevel', dest='loglevel', action='store', choices=log_levels, default='WARNING', help='control verbosity of logging')
    subparsers = parser.add_subparsers(title='commands')

    parser_new_release = subparsers.add_parser('new-release', help='create a new release')
    parser_new_release.add_argument('name', type=str, action='store', help='name of this release (e.g., quirm)')
    parser_new_release.add_argument('buildroot', type=str, action='store', help='a compiled OpenWRT buildroot for the release')
    parser_new_release.set_defaults(handler=commands.new_release)

    parser_list_releases = subparsers.add_parser('list-releases', help='list all releases')
    parser_list_releases.set_defaults(handler=commands.list_releases)

    parser_list_architectures = subparsers.add_parser('list-architectures', help='list architectures for a release')
    parser_list_architectures.add_argument('release', type=str, action='store', help='name of the release (e.g., quirm)')
    parser_list_architectures.set_defaults(handler=commands.list_architectures)

    parser_list_builtin_packages = subparsers.add_parser('list-builtin-packages', help='list builtin packages for a release')
    parser_list_builtin_packages.add_argument('release', type=str, action='store', help='name of the release (e.g., quirm)')
    parser_list_builtin_packages.add_argument('architecture', type=str, nargs='?', action='store', help='target architecture (e.g., ar71xx)')
    parser_list_builtin_packages.set_defaults(handler=commands.list_builtin_packages)

    parser_add_packages = subparsers.add_parser('add-packages', help='create a new release')
    parser_add_packages.add_argument('release', type=str, action='store', help='add packages for this release (e.g., quirm)')
    parser_add_packages.add_argument('ipk', nargs='+', type=str, action='store', help='a compiled OpenWRT buildroot for the release')
    parser_add_packages.set_defaults(handler=commands.add_packages)

    parser_list_groups = subparsers.add_parser('list-groups', help='list names of all groups')
    parser_list_groups.set_defaults(handler=commands.list_groups)

    parser_list_group = subparsers.add_parser('list-group', help='list nodes in a groups')
    parser_list_group.add_argument('name', type=str, action='store', help='name of the new group')
    parser_list_group.set_defaults(handler=commands.list_group)

    parser_new_group = subparsers.add_parser('new-group', help='create a new group of nodes')
    parser_new_group.add_argument('name', type=str, action='store', help='name of the new group')
    parser_new_group.add_argument('node', nargs='*', type=str, action='store', help='nodes to add')
    parser_new_group.set_defaults(handler=commands.new_group)

    parser_delete_group = subparsers.add_parser('delete-group', help='delete group of nodes')
    parser_delete_group.add_argument('name', type=str, action='store', help='name of the group to delete')
    parser_delete_group.set_defaults(handler=commands.delete_group)

    parser_add_to_group = subparsers.add_parser('add-to-group', help='add nodes to a group')
    parser_add_to_group.add_argument('group', type=str, action='store', help='name of the group')
    parser_add_to_group.add_argument('node', nargs='+', type=str, action='store', help='nodes to add')
    parser_add_to_group.set_defaults(handler=commands.add_to_group)

    parser_remove_from_group = subparsers.add_parser('remove-from-group', help='remove nodes from a group')
    parser_remove_from_group.add_argument('group', type=str, action='store', help='name of the group')
    parser_remove_from_group.add_argument('node', nargs='+', type=str, action='store', help='nodes to remove')
    parser_remove_from_group.set_defaults(handler=commands.remove_from_group)

    parser_upgrade_package = subparsers.add_parser('upgrade-package', help='upgrade a builtin package on a set of routers')
    parser_upgrade_package.add_argument('release', type=str, action='store', help='upgrade package for this release (e.g., quirm)')
    parser_upgrade_package.add_argument('architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_upgrade_package.add_argument('package', type=str, action='store', help='name of the builtin package to upgrade')
    parser_upgrade_package.add_argument('version', type=str, action='store', help='new version of the package')
    parser_upgrade_package.add_argument('group', nargs='+', type=str, action='store', help='upgrade on this group of routers')
    parser_upgrade_package.set_defaults(handler=commands.upgrade_package)

    parser_list_upgrades = subparsers.add_parser('list-upgrades', help='list package upgrades for nodes')
    parser_list_upgrades.add_argument('release', type=str, action='store', help='show upgrades from this release (e.g., quirm)')
    parser_list_upgrades.add_argument('architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_list_upgrades.add_argument('group', type=str, action='store', help='upgrade on this group of routers')
    parser_list_upgrades.add_argument('package', nargs='*', type=str, action='store', help='show upgrades of these packages')
    parser_list_upgrades.set_defaults(handler=commands.list_upgrades)

    parser_commit = subparsers.add_parser('commit', help='commit current release configuration to git')
    parser_commit.set_defaults(handler=commands.commit)

    parser_deploy = subparsers.add_parser('deploy', help='deploy all releases')
    parser_deploy.add_argument('destination', type=str, action='store', help='deploy to this directory')
    parser_deploy.set_defaults(handler=commands.deploy)

    args = parser.parse_args()
    args.root = os.path.expanduser(args.root)

    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=getattr(logging, args.loglevel))

    args.handler(args)

if __name__ == '__main__':
    main()
