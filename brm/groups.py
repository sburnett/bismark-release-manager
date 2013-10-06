import errno
import glob
import os

class NodeGroups(object):
    _reserved_groups = set(['default'])

    def __init__(self, root):
        self._root = root
        self._groups = dict()
        self._groups_to_delete = set()

        pattern = os.path.join(self._root, '*')
        for filename in glob.iglob(pattern):
            if not os.path.isfile(filename):
                continue
            name = os.path.basename(filename)
            with open(filename) as handle:
                self._groups[name] = set()
                for line in handle:
                    self._groups[name].add(line.strip())

    @property
    def groups(self):
        return self._groups.keys()

    def nodes_in_group(self, name):
        return self._groups[name]

    def new_group(self, name):
        if name in self._reserved_groups:
            raise Exception('that group name is reserved')
        if name in self._groups:
            raise Exception('group already exists')
        self._groups[name] = set()
        self._groups_to_delete.discard(name)

    def delete_group(self, name):
        del self._groups[name]
        self._groups_to_delete.add(name)

    def add_to_group(self, name, node):
        self._groups[name].add(node)

    def remove_from_group(self, name, node):
        self._groups[name].remove(node)

    def write_to_files(self):
        try:
            os.makedirs(self._root)
        except OSError as err:
            if err.errno == errno.EEXIST:
                pass
            else:
                raise
        for name, nodes in self._groups.items():
            filename = os.path.join(self._root, name)
            with open(filename, 'w') as handle:
                for node in sorted(nodes):
                    print >>handle, node
        for name in self._groups_to_delete:
            filename = os.path.join(self._root, name)
            try:
                os.remove(filename)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

