from collections import namedtuple
import glob
import os

import common

ExperimentConflict = namedtuple('ExperimentConflict', ['name'])
ExperimentPackage = namedtuple('ExperimentPackage',
                               ['group',
                                'release',
                                'name',
                                'version',
                                'architecture'])
GroupName = namedtuple('GroupList', ['group'])

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
        self._conflicts = common.NamedTupleSet(ExperimentConflict,
                                               self._get_filename('conflicts'))
        self._packages = common.NamedTupleSet(ExperimentPackage,
                                              self._get_filename('packages'))
        self._installed = common.NamedTupleSet(GroupName,
                                               self._get_filename('installed'))
        self._required = common.NamedTupleSet(GroupName,
                                              self._get_filename('required'))
        self._revoked = common.NamedTupleSet(GroupName,
                                             self._get_filename('revoked'))

    @property
    def packages(self):
        return self._packages

    def add_package(self, *args):
        experiment_package = ExperimentPackage(*args)
        self._packages.add(experiment_package)

    def remove_package(self, *args):
        experiment_package = ExperimentPackage(*args)
        self._packages.remove(experiment_package)

    def require(self, group):
        self._required.add(GroupName(group))

    def unrequire(self, group):
        self._required.remove(GroupName(group))

    def write_to_files(self):
        common.makedirs(self._root)
        with open(self._get_filename('description'), 'w') as handle:
            handle.write(self._description)
        with open(self._get_filename('display-name'), 'w') as handle:
            handle.write(self._display_name)
        self._conflicts.write_to_file()
        self._packages.write_to_file()
        self._installed.write_to_file()
        self._required.write_to_file()
        self._revoked.write_to_file()

    def _get_filename(self, name):
        return os.path.join(self._root, name)

    def _read_from_files(self):
        with open(self._get_filename('description')) as handle:
            self._description = handle.read()
        with open(self._get_filename('display-name')) as handle:
            self._display_name = handle.read()

        with open(self._get_filename('conflicts')) as handle:
            for line in handle:
                conflicting_experiment = ExperimentConflict(line.strip())
                self._conflicts.add(conflicting_experiment)
        self._packages.read_from_file()


class BismarkExperiments(object):
    def __init__(self, root):
        self._root = root
        self._experiments = {}

        pattern = os.path.join(self._root, '*')
        for dirname in glob.iglob(pattern):
            if not os.path.isdir(dirname):
                continue
            name = os.path.basename(dirname)
            experiment = open_experiment(dirname)
            self._experiments[name] = experiment

    @property
    def experiments(self):
        return self._experiments

    def experiment_packages(self, experiment):
        return self._experiment(experiment).packages

    def new_experiment(self, name, *rest):
        if name in self._experiments:
            raise Exception('experiment already exists')
        experiment_path = self._experiment_path(name)
        self._experiments[name] = new_experiment(experiment_path, *rest)

    def add_to_experiment(self, experiment, *rest):
        self._experiment(experiment).add_package(*rest)

    def remove_from_experiment(self, experiment, *rest):
        self._experiment(experiment).remove_package(*rest)

    def require_experiment(self, experiment, group):
        self._experiment(experiment).require(group)

    def unrequire_experiment(self, experiment, group):
        self._experiment(experiment).unrequire(group)

    def write_to_files(self):
        for name, experiment in self._experiments.items():
            experiment.write_to_files()

    def _experiment(self, name):
        if name not in self._experiments:
            raise Exception('experiment does not exist')
        return self._experiments[name]

    def _experiment_path(self, name):
        return os.path.join(self._root, name)
