#!/usr/bin/env python2.7

import argparse
import os

from commands import new_release, list_releases, list_architectures, list_builtin_packages

def main():
    parser = argparse.ArgumentParser(description='Publish releases of BISmark images, packages, and experiments')
    parser.add_argument('--root', dest='root', action='store', default='~/bismark-releases', help='store release configuration in this directory')
    subparsers = parser.add_subparsers(title='commands')

    parser_new_release = subparsers.add_parser('new-release', help='create a new release')
    parser_new_release.add_argument('name', type=str, action='store', help='name of this release (e.g., quirm)')
    parser_new_release.add_argument('buildroot', type=str, action='store', help='a compiled OpenWRT buildroot for the release')
    parser_new_release.set_defaults(handler=new_release.run)

    parser_list_releases = subparsers.add_parser('list-releases', help='list all releases')
    parser_list_releases.set_defaults(handler=list_releases.run)

    parser_list_architectures = subparsers.add_parser('list-architectures', help='list architectures for a release')
    parser_list_architectures.add_argument('release', type=str, action='store', help='name of the release (e.g., quirm)')
    parser_list_architectures.set_defaults(handler=list_architectures.run)

    parser_list_builtin_packages = subparsers.add_parser('list-builtin-packages', help='list builtin packages for a release')
    parser_list_builtin_packages.add_argument('release', type=str, action='store', help='name of the release (e.g., quirm)')
    parser_list_builtin_packages.add_argument('architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_list_builtin_packages.set_defaults(handler=list_builtin_packages.run)

    args = parser.parse_args()
    args.root = os.path.expanduser(args.root)
    result = args.handler(args)
    if result is not None:
        print result

if __name__ == '__main__':
    main()
