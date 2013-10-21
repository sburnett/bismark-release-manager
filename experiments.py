from collections import defaultdict, namedtuple
import glob
import logging
import os

import common

ExperimentConflict = namedtuple('ExperimentConflict', ['name'])
ExperimentPackage = namedtuple('ExperimentPackage',
                               ['group',
                                'release',
                                'name',
                                'version',
                                'architecture'])
GroupName = namedtuple('GroupName', ['group'])


def new_experiment(root, display_name, description):
    experiment = _Experiment(root)
    experiment._display_name = display_name
    experiment._description = description
    return experiment


def open_experiment(root):
    experiment = _Experiment(root)
    experiment._read_from_files()
    return experiment


class _Experiment(object):

    def __init__(self, root):
        self._root = root
        self._name = os.path.basename(root)
        self._conflicts = common.NamedTupleSet(ExperimentConflict,
                                               self._get_filename('conflicts'))
        self._packages = common.NamedTupleSet(ExperimentPackage,
                                              self._get_filename('packages'))
        self._installed_by_default = common.NamedTupleSet(
            GroupName,
            self._get_filename('installed-by-default'))
        self._required = common.NamedTupleSet(GroupName,
                                              self._get_filename('required'))
        self._revoked = common.NamedTupleSet(GroupName,
                                             self._get_filename('revoked'))

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        return self._display_name

    @property
    def description(self):
        return self._description

    @property
    def header_groups(self):
        groups = set()
        for group_name in self._installed_by_default:
            groups.add(group_name.group)
        for group_name in self._required:
            groups.add(group_name.group)
        for group_name in self._revoked:
            groups.add(group_name.group)
        groups.add('default')
        return groups

    @property
    def packages(self):
        return self._packages

    def add_package(self, *args):
        experiment_package = ExperimentPackage(*args)
        self._packages.add(experiment_package)

    def remove_package(self, *args):
        experiment_package = ExperimentPackage(*args)
        self._packages.remove(experiment_package)

    @property
    def conflicts(self):
        conflicts = set()
        for conflict in self._conflicts:
            conflicts.add(conflict.name)
        return conflicts

    def add_conflict(self, conflict_name):
        self._conflicts.add(ExperimentConflict(conflict_name))

    def remove_conflict(self, conflict_name):
        self._conflicts.remove(ExperimentConflict(conflict_name))

    @property
    def required(self):
        required = set()
        for group in self._required:
            required.add(group.group)
        return required

    def is_required(self, group):
        return GroupName(group) in self._required

    def set_required(self, group, required):
        if required:
            self._required.add(GroupName(group))
        else:
            self._required.discard(GroupName(group))

    @property
    def installed_by_default(self):
        installed = set()
        for group in self._installed_by_default:
            installed.add(group.group)
        return installed

    def is_installed_by_default(self, group):
        return GroupName(group) in self._installed_by_default

    def set_installed_by_default(self, group, installed_by_default):
        if installed_by_default:
            self._installed_by_default.add(GroupName(group))
        else:
            self._installed_by_default.discard(GroupName(group))

    @property
    def revoked(self):
        revoked = set()
        for group in self._revoked:
            revoked.add(group.group)
        return revoked

    def is_revoked(self, group):
        return GroupName(group) in self._revoked

    def set_revoked(self, group, revoked):
        if revoked:
            self._revoked.add(GroupName(group))
        else:
            self._revoked.discard(GroupName(group))

    def group_packages(self, release_name):
        group_packages = defaultdict(set)
        for package in self._packages:
            if package.release != release_name:
                continue
            group_packages[package.group].add(package)
        return group_packages

    def write_to_files(self):
        common.makedirs(self._root)
        with open(self._get_filename('description'), 'w') as handle:
            handle.write(self._description)
        with open(self._get_filename('display-name'), 'w') as handle:
            handle.write(self._display_name)
        self._conflicts.write_to_file()
        self._packages.write_to_file()
        self._installed_by_default.write_to_file()
        self._required.write_to_file()
        self._revoked.write_to_file()

    def _read_from_files(self):
        with open(self._get_filename('description')) as handle:
            self._description = handle.read()
        with open(self._get_filename('display-name')) as handle:
            self._display_name = handle.read()
        self._conflicts.read_from_file()
        self._packages.read_from_file()
        self._installed_by_default.read_from_file()
        self._required.read_from_file()
        self._revoked.read_from_file()

    def _get_filename(self, name):
        return os.path.join(self._root, name)


class Experiments(object):

    def __init__(self, root):
        self._root = root
        self._experiments = {}

        self._read_from_files()

    def __iter__(self):
        return self._experiments.__iter__()

    def __getitem__(self, name):
        if name not in self._experiments:
            raise Exception('experiment does not exist')
        return self._experiments[name]

    def iteritems(self):
        return self._experiments.iteritems()

    def new_experiment(self, name, *rest):
        if name in self._experiments:
            raise Exception('experiment already exists')
        experiment_path = self._experiment_path(name)
        self._experiments[name] = new_experiment(experiment_path, *rest)

    def check_constraints(self):
        self._check_required_experiments_conflict()

    def _check_required_experiments_conflict(self):
        logging.info('Check if required experiments conflict')
        must_be_installed = set()
        cannot_be_installed = set()
        for name, experiment in self.iteritems():
            if not experiment.required:
                continue
            must_be_installed.add(experiment.name)
            cannot_be_installed.update(experiment.conflicts)
        if must_be_installed.intersection(cannot_be_installed):
            raise Exception('Required experiments conflict: %r vs %r' % (
                must_be_installed, cannot_be_installed))

    def write_to_files(self):
        self.check_constraints()
        for name, experiment in self._experiments.items():
            experiment.write_to_files()

    def _read_from_files(self):
        pattern = os.path.join(self._root, '*')
        for dirname in glob.iglob(pattern):
            if not os.path.isdir(dirname):
                continue
            name = os.path.basename(dirname)
            self._experiments[name] = open_experiment(dirname)

    def _experiment_path(self, name):
        return os.path.join(self._root, name)
