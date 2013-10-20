import errno
import glob
import logging
import os

class NodeGroups(object):
    _reserved_groups = set(['default'])

    def __init__(self, root):
        self._root = root
        self._groups = dict()
        self._groups_to_delete = set()

        self._read_from_files()

    def __iter__(self):
        return self._groups.__iter__()

    def __getitem__(self, name):
        return self._groups[name]

    def __delitem__(self, name):
        del self._groups[name]
        self._groups_to_delete.add(name)
        logging.info('Deleted group %r', name)

    def new_group(self, name):
        if name in self._reserved_groups:
            raise Exception('that group name is reserved')
        if name in self._groups:
            raise Exception('group already exists')
        self._groups[name] = set()
        self._groups_to_delete.discard(name)
        logging.info('Created new group %r', name)

    def resolve_to_nodes(self, group_or_node):
        if group_or_node in self._groups:
            logging.info('resolving %r to a set of nodes', group_or_node)
            return self._groups[group_or_node]
        else:
            logging.info('resolving %r to a single node', group_or_node)
            return set([group_or_node])

    def write_to_files(self):
        logging.info('Writing groups in %r', self._root)
        try:
            os.makedirs(self._root)
            logging.info('Creating groups directory %r', self._root)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
            logging.info('Groups directory %r already exists', self._root)
        for name, nodes in self._groups.items():
            filename = os.path.join(self._root, name)
            logging.info('Writing group %r to %r', name, filename)
            with open(filename, 'w') as handle:
                for node in sorted(nodes):
                    print >>handle, node
                    logging.info('Wrote node %r for group %r', node, name)
        logging.info('Removing deleted group files')
        for name in self._groups_to_delete:
            filename = os.path.join(self._root, name)
            logging.info('Removing group file %r', filename)
            try:
                os.remove(filename)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

    def _read_from_files(self):
        pattern = os.path.join(self._root, '*')
        logging.info('Reading groups from %r', pattern)
        for filename in glob.iglob(pattern):
            if not os.path.isfile(filename):
                logging.info('%r is not a group', filename)
                continue
            name = os.path.basename(filename)
            logging.info('Reading group %r from %r', name, filename)
            with open(filename) as handle:
                self._groups[name] = set()
                for line in handle:
                    node = line.strip()
                    logging.info('Reading node %r for group %r', node, name)
                    self._groups[name].add(node)
