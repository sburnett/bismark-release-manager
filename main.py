#!/usr/bin/env python2.7

import argparse
import logging
import os

import subcommands
import tree


def create_groups_subcommands(subparsers):
    parser_list_group = subparsers.add_parser(
        'list', help='list nodes in a groups')
    parser_list_group.add_argument(
        'name', type=str, nargs='?', action='store', help='name of the group to list')
    parser_list_group.set_defaults(handler=subcommands.list_group)

    parser_list_all_groups = subparsers.add_parser(
        'list-all', help='list all groups of nodes')
    parser_list_all_groups.set_defaults(handler=subcommands.list_all_groups)

    parser_new_group = subparsers.add_parser(
        'new', help='create a new group of nodes')
    parser_new_group.add_argument(
        'name', type=str, action='store', help='name of the new group')
    parser_new_group.add_argument(
        'node', nargs='*', type=str, action='store', help='nodes to add')
    parser_new_group.set_defaults(handler=subcommands.new_group)

    parser_copy_group = subparsers.add_parser(
        'copy', help='copy a group of nodes')
    parser_copy_group.add_argument(
        'name', type=str, action='store', help='name of the group to copy')
    parser_copy_group.add_argument(
        'new_name', type=str, action='store', help='name of the new copy')
    parser_copy_group.set_defaults(handler=subcommands.copy_group)

    parser_delete_group = subparsers.add_parser(
        'delete', help='delete a group of nodes')
    parser_delete_group.add_argument(
        'name', type=str, action='store', help='name of the group to delete')
    parser_delete_group.set_defaults(handler=subcommands.delete_group)

    parser_add_to_group = subparsers.add_parser(
        'add-nodes', help='add nodes to a group')
    parser_add_to_group.add_argument(
        'group', type=str, action='store', help='name of the group')
    parser_add_to_group.add_argument(
        'node', nargs='+', type=str, action='store', help='nodes to add')
    parser_add_to_group.set_defaults(handler=subcommands.add_to_group)

    parser_remove_from_group = subparsers.add_parser(
        'remove-nodes', help='remove nodes from a group')
    parser_remove_from_group.add_argument(
        'group', type=str, action='store', help='name of the group')
    parser_remove_from_group.add_argument(
        'node', nargs='+', type=str, action='store', help='nodes to remove')
    parser_remove_from_group.set_defaults(
        handler=subcommands.remove_from_group)


def create_experiments_subcommands(subparsers):
    parser_new_experiment = subparsers.add_parser(
        'new', help='create a new experiment')
    parser_new_experiment.add_argument(
        'name', type=str, action='store', help='name of the new experiment')
    parser_new_experiment.set_defaults(handler=subcommands.new_experiment)

    parser_add_to_experiment = subparsers.add_parser(
        'add-package', help='add a package to an experiment')
    parser_add_to_experiment.add_argument(
        'experiment', type=str, action='store', help='experiment identifier')
    parser_add_to_experiment.add_argument(
        'group', type=str, action='store', help='enable experiment on this group of routers')
    parser_add_to_experiment.add_argument(
        'release', type=str, action='store', help='add package for this release (e.g., quirm)')
    parser_add_to_experiment.add_argument(
        'architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_add_to_experiment.add_argument(
        'package', type=str, action='store', help='name of the package to install')
    parser_add_to_experiment.add_argument(
        'version', type=str, action='store', help='version of the package')
    parser_add_to_experiment.set_defaults(
        handler=subcommands.add_to_experiment)

    parser_remove_from_experiment = subparsers.add_parser(
        'remove-package', help='remove a package from an experiment')
    parser_remove_from_experiment.add_argument(
        'experiment', type=str, action='store', help='experiment identifier')
    parser_remove_from_experiment.add_argument(
        'group', type=str, action='store', help='remove packages from this group of routers')
    parser_remove_from_experiment.add_argument(
        'release', type=str, action='store', help='remove package from this release (e.g., quirm)')
    parser_remove_from_experiment.add_argument(
        'architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_remove_from_experiment.add_argument(
        'package', type=str, action='store', help='name of the package')
    parser_remove_from_experiment.add_argument(
        'version', type=str, action='store', help='version of the package')
    parser_remove_from_experiment.set_defaults(
        handler=subcommands.remove_from_experiment)

    parser_list_experiment = subparsers.add_parser(
        'list', help='list experiment details')
    parser_list_experiment.add_argument(
        'experiment', type=str, nargs='?', action='store', help='list details for this experiment')
    parser_list_experiment.set_defaults(handler=subcommands.list_experiment)

    parser_list_experiment = subparsers.add_parser(
        'list-all', help='list all experiments')
    parser_list_experiment.set_defaults(
        handler=subcommands.list_all_experiments)

    parser_list_experiment_packages = subparsers.add_parser(
        'list-packages', help='list packages for an experiment')
    parser_list_experiment_packages.add_argument(
        'experiment', type=str, action='store', help='list packages for this experiment')
    parser_list_experiment_packages.set_defaults(
        handler=subcommands.list_experiment_packages)

    parser_install_by_default = subparsers.add_parser(
        'install-by-default', help='Install an experiment by default')
    parser_install_by_default.add_argument(
        'experiment', type=str, action='store', help='name of the experiment')
    parser_install_by_default.add_argument(
        'group', nargs='+', type=str, action='store', help='install by default on these routers')
    parser_install_by_default.set_defaults(
        handler=subcommands.install_by_default)

    parser_uninstall_by_default = subparsers.add_parser(
        'uninstall-by-default', help="Don't Install an experiment by default")
    parser_uninstall_by_default.add_argument(
        'experiment', type=str, action='store', help='name of the experiment')
    parser_uninstall_by_default.add_argument(
        'group', nargs='+', type=str, action='store', help='install by default on these routers')
    parser_uninstall_by_default.set_defaults(
        handler=subcommands.uninstall_by_default)

    parser_require_experiment = subparsers.add_parser(
        'require', help='require a group of routers to install an experiment')
    parser_require_experiment.add_argument(
        'experiment', type=str, action='store', help='name of the experiment')
    parser_require_experiment.add_argument(
        'group', nargs='+', type=str, action='store', help='require the experiment on these routers')
    parser_require_experiment.set_defaults(
        handler=subcommands.require_experiment)

    parser_unrequire_experiment = subparsers.add_parser(
        'unrequire', help='stop requiring a group of routers to install an experiment')
    parser_unrequire_experiment.add_argument(
        'experiment', type=str, action='store', help='name of the experiment')
    parser_unrequire_experiment.add_argument(
        'group', nargs='+', type=str, action='store', help='stop requiring the experiment on these routers')
    parser_unrequire_experiment.set_defaults(
        handler=subcommands.unrequire_experiment)

    parser_revoke_experiment = subparsers.add_parser(
        'revoke', help='revoke an experiment on a group of routers')
    parser_revoke_experiment.add_argument(
        'experiment', type=str, action='store', help='name of the experiment')
    parser_revoke_experiment.add_argument(
        'group', nargs='+', type=str, action='store', help='revoke the experiment on these routers')
    parser_revoke_experiment.set_defaults(
        handler=subcommands.revoke_experiment)

    parser_unrevoke_experiment = subparsers.add_parser(
        'unrevoke', help='stop revoking a group of routers to install an experiment')
    parser_unrevoke_experiment.add_argument(
        'experiment', type=str, action='store', help='name of the experiment')
    parser_unrevoke_experiment.add_argument(
        'group', nargs='+', type=str, action='store', help='stop revoking the experiment on these routers')
    parser_unrevoke_experiment.set_defaults(
        handler=subcommands.unrevoke_experiment)


def create_packages_subcommands(subparsers):
    parser_add_packages = subparsers.add_parser(
        'import', help='import ipk files for a release')
    parser_add_packages.add_argument(
        'release', type=str, action='store', help='import packages for this release (e.g., quirm)')
    parser_add_packages.add_argument(
        'ipk', nargs='+', type=str, action='store', help='ipkg files to import')
    parser_add_packages.set_defaults(handler=subcommands.add_packages)

    parser_list_packages = subparsers.add_parser(
        'list', help='list available packages')
    parser_list_packages.add_argument(
        'release', type=str, nargs='?', action='store', help='list packages for this release (e.g., quirm)')
    parser_list_packages.set_defaults(handler=subcommands.list_packages)

    parser_list_builtin_packages = subparsers.add_parser(
        'list-builtin', help='list builtin packages for a release')
    parser_list_builtin_packages.add_argument(
        'release', type=str, nargs='?', action='store', help='name of the release (e.g., quirm)')
    parser_list_builtin_packages.add_argument(
        'architecture', type=str, nargs='?', action='store', help='target architecture (e.g., ar71xx)')
    parser_list_builtin_packages.set_defaults(
        handler=subcommands.list_builtin_packages)

    parser_list_extra_packages = subparsers.add_parser(
        'list-extra', help='list "extra" packages for a release')
    parser_list_extra_packages.add_argument(
        'release', type=str, nargs='?', action='store', help='name of the release (e.g., quirm)')
    parser_list_extra_packages.add_argument(
        'architecture', type=str, nargs='?', action='store', help='target architecture (e.g., ar71xx)')
    parser_list_extra_packages.set_defaults(
        handler=subcommands.list_extra_packages)

    parser_list_upgrades = subparsers.add_parser(
        'list-upgrades', help='list package upgrades for nodes')
    parser_list_upgrades.add_argument(
        'release', type=str, nargs='?', action='store', help='show upgrades from this release (e.g., quirm)')
    parser_list_upgrades.set_defaults(handler=subcommands.list_upgrades)

    parser_remove_extra_package = subparsers.add_parser(
        'remove-from-extra', help='remove packages from the "extra" set')
    parser_remove_extra_package.add_argument(
        'release', type=str, action='store', help='remove package from this release (e.g., quirm)')
    parser_remove_extra_package.add_argument(
        'architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_remove_extra_package.add_argument(
        'package', type=str, action='store', help='name of the package to remove')
    parser_remove_extra_package.add_argument(
        'version', type=str, action='store', help='version of the package')
    parser_remove_extra_package.set_defaults(
        handler=subcommands.remove_extra_package)

    parser_add_extra_package = subparsers.add_parser(
        'add-to-extra', help='add packages to the "extra" set')
    parser_add_extra_package.add_argument(
        'release', type=str, action='store', help='add package from this release (e.g., quirm)')
    parser_add_extra_package.add_argument(
        'architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_add_extra_package.add_argument(
        'package', type=str, action='store', help='name of the package to add')
    parser_add_extra_package.add_argument(
        'version', type=str, action='store', help='version of the package')
    parser_add_extra_package.set_defaults(
        handler=subcommands.add_extra_package)

    parser_upgrade_package = subparsers.add_parser(
        'upgrade', help='upgrade a builtin package on a set of routers')
    parser_upgrade_package.add_argument(
        'group', type=str, action='store', help='upgrade on this group of routers')
    parser_upgrade_package.add_argument(
        'release', type=str, action='store', help='upgrade package for this release (e.g., quirm)')
    parser_upgrade_package.add_argument(
        'architecture', type=str, action='store', help='target architecture (e.g., ar71xx)')
    parser_upgrade_package.add_argument(
        'package', type=str, action='store', help='name of the builtin package to upgrade')
    parser_upgrade_package.add_argument(
        'version', type=str, action='store', help='new version of the package')
    parser_upgrade_package.set_defaults(handler=subcommands.upgrade_package)


def create_releases_subcommands(subparsers):
    parser_list_releases = subparsers.add_parser(
        'list', help='list all releases')
    parser_list_releases.set_defaults(handler=subcommands.list_releases)

    parser_list_architectures = subparsers.add_parser(
        'list-architectures', help='list architectures for a release')
    parser_list_architectures.add_argument(
        'release', type=str, action='store', help='name of the release (e.g., quirm)')
    parser_list_architectures.set_defaults(
        handler=subcommands.list_architectures)

    parser_new_release = subparsers.add_parser(
        'new', help='create a new release')
    parser_new_release.add_argument(
        'name', type=str, action='store', help='name of this release (e.g., quirm)')
    parser_new_release.add_argument(
        'buildroot', type=str, action='store', help='a compiled OpenWRT buildroot for the release')
    parser_new_release.set_defaults(handler=subcommands.new_release)


def main():
    parser = argparse.ArgumentParser(
        description='Publish releases of BISmark images, packages, and experiments')
    parser.add_argument('--root', dest='root', action='store',
                        default='~/bismark-releases', help='store release configuration in this directory')
    log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITITCAL']
    parser.add_argument('--loglevel', dest='loglevel', action='store',
                        choices=log_levels, default='WARNING', help='control verbosity of logging')
    parser.add_argument('--logfile', dest='logfile', action='store',
                        default=None, help='append logs to this file')
    subparsers = parser.add_subparsers(title='commands')

    parser_groups = subparsers.add_parser(
        'groups', help='Manage groups of nodes')
    groups_subparsers = parser_groups.add_subparsers(title='group subcommands')
    create_groups_subcommands(groups_subparsers)

    parser_experiments = subparsers.add_parser(
        'experiments', help='Manage experiments')
    experiments_subparsers = parser_experiments.add_subparsers(
        title='experiments subcommands')
    create_experiments_subcommands(experiments_subparsers)

    parser_packages = subparsers.add_parser('packages', help='Manage packages')
    packages_subparsers = parser_packages.add_subparsers(
        title='packages subcommands')
    create_packages_subcommands(packages_subparsers)

    parser_releases = subparsers.add_parser('releases', help='Manage releases')
    releases_subparsers = parser_releases.add_subparsers(
        title='releases subcommands')
    create_releases_subcommands(releases_subparsers)

    parser_commit = subparsers.add_parser(
        'commit', help='commit current release configuration to git')
    parser_commit.set_defaults(handler=subcommands.commit)

    parser_diff = subparsers.add_parser(
        'diff', help='show changes ready to be committed to git')
    parser_diff.set_defaults(handler=subcommands.diff)

    parser_deploy = subparsers.add_parser('deploy',
                                          help='deploy all releases',
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_deploy.add_argument(
        '-d', '--destination', type=str,
        default='bismark-downloads.noise.gatech.edu:/var/www/downloads.projectbismark.net',
        action='store', help='deploy to this directory')
    parser_deploy.add_argument(
        '-k', '--signingkey', type=str,
        default='~/.bismark_signing_key.pem',
        action='store', help='sign Packages.gz with this key')
    parser_deploy.set_defaults(handler=subcommands.deploy)

    parser_deploy = subparsers.add_parser(
        'check', help='check validity of the release configuration')
    parser_deploy.set_defaults(handler=subcommands.check)

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        filename=args.logfile,
                        level=getattr(logging, args.loglevel))

    releases_tree = tree.BismarkReleasesTree(os.path.expanduser(args.root))
    args.handler(releases_tree, args)

if __name__ == '__main__':
    main()
