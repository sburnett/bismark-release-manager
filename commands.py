import os


def add_extra_package(releases_tree, args):
    releases_tree.add_extra_package(args.release,
                                    args.package,
                                    args.version,
                                    args.architecture)


def add_packages(releases_tree, args):
    releases_tree.add_packages(args.release, args.ipk)


def add_to_experiment(releases_tree, args):
    releases_tree.add_to_experiment(args.experiment,
                                    args.group,
                                    args.release,
                                    args.package,
                                    args.version,
                                    args.architecture)


def add_to_group(releases_tree, args):
    releases_tree.add_to_group(args.group, args.node)


def commit(releases_tree, args):
    releases_tree.commit()


def delete_group(releases_tree, args):
    releases_tree.delete_group(args.name)


def deploy(releases_tree, args):
    releases_tree.deploy(args.destination)


def install_by_default(releases_tree, args):
    releases_tree.set_experiment_installed_by_default(args.experiment,
                                                      True,
                                                      args.group)


def uninstall_by_default(releases_tree, args):
    releases_tree.set_experiment_installed_by_default(args.experiment,
                                                      False,
                                                      args.group)


def list_architectures(releases_tree, args):
    for architecture in sorted(releases_tree.architectures(args.release)):
        print ' '.join(architecture)


def list_builtin_packages(releases_tree, args):
    for package in sorted(releases_tree.builtin_packages(args.release)):
        if (args.architecture is not None and
                package.architecture != args.architecture):
            continue
        print ' '.join(package)


def list_experiment(releases_tree, args):
    if args.experiment is None:
        for name in sorted(releases_tree.experiments):
            print name
        return

    experiment = releases_tree.experiments[args.experiment]
    print 'Name:', experiment.name
    print 'Display name:', experiment.display_name
    print 'Description:', experiment.description
    print 'Required:', ', '.join(experiment.required)
    print 'Revoked:', ', '.join(experiment.revoked)
    print 'Installed by default:', ', '.join(experiment.installed_by_default)
    print 'Explicit conflicts:', ', '.join(experiment.conflicts)
    implicit_conflicts = set()
    for name, experiment in releases_tree.experiments.iteritems():
        if name == args.experiment:
            continue
        if args.experiment not in experiment.conflicts:
            continue
        implicit_conflicts.add(name)
    print 'Implicit conflicts:', ', '.join(implicit_conflicts)


def list_experiment_packages(releases_tree, args):
    for package in sorted(releases_tree.experiment_packages(args.experiment)):
        print ' '.join(package)


def list_extra_packages(releases_tree, args):
    for package in sorted(releases_tree.extra_packages(args.release)):
        if (args.architecture is not None and
                package.architecture != args.architecture):
            continue
        print ' '.join(package)


def list_group(releases_tree, args):
    if args.name is None:
        for group in releases_tree.groups:
            print group
    else:
        for node in sorted(releases_tree.nodes_in_group(args.name)):
            print node


def list_packages(releases_tree, args):
    for package in sorted(releases_tree.packages(args.release)):
        print ' '.join(package)


def list_releases(releases_tree, args):
    for release_name in releases_tree.releases:
        print release_name


def list_upgrades(releases_tree, args):
    upgrades = releases_tree.upgrades(args.release,
                                      args.architecture,
                                      args.group,
                                      args.package)
    for upgrade in sorted(upgrades):
        print ' '.join(upgrade)


def new_experiment(releases_tree, args):
    display_name = raw_input('Enter a display name for this experiment: ')
    description = raw_input('Enter a description for this experiment: ')
    releases_tree.new_experiment(args.name, display_name, description)


def new_group(releases_tree, args):
    releases_tree.new_group(args.name)
    releases_tree.add_to_group(args.name, args.node)


def new_release(releases_tree, args):
    openwrt_build_root = os.path.expanduser(args.buildroot)
    releases_tree.new_release(args.name, openwrt_build_root)


def remove_extra_package(releases_tree, args):
    releases_tree.remove_extra_package(args.release,
                                       args.package,
                                       args.version,
                                       args.architecture)


def remove_from_experiment(releases_tree, args):
    releases_tree.remove_from_experiment(args.experiment,
                                         args.group,
                                         args.release,
                                         args.package,
                                         args.version,
                                         args.architecture)


def remove_from_group(releases_tree, args):
    releases_tree.remove_from_group(args.group, args.node)


def require_experiment(releases_tree, args):
    releases_tree.set_experiment_required(args.experiment, True, args.group)


def unrequire_experiment(releases_tree, args):
    releases_tree.set_experiment_required(args.experiment, False, args.group)


def upgrade_package(releases_tree, args):
    releases_tree.upgrade_package(args.release,
                                  args.package,
                                  args.version,
                                  args.architecture,
                                  args.group)