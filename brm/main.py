#!/usr/bin/env python2.7

import argparse
import logging
import os
import sys

import commands

def main():
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

    parser = argparse.ArgumentParser(description='Publish releases of BISmark images, packages, and experiments')
    parser.add_argument('--root', dest='root', action='store', default='~/bismark-releases', help='store release configuration in this directory')
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

    args = parser.parse_args()
    args.root = os.path.expanduser(args.root)
    result = args.handler(args)
    if result is not None:
        print result
        sys.exit(1)

if __name__ == '__main__':
    main()
