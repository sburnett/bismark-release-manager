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
        logging.info('Created new group %r', name)

    def delete_group(self, name):
        del self._groups[name]
        self._groups_to_delete.add(name)
        logging.info('Deleted group %r', name)

    def add_to_group(self, name, node):
        self._groups[name].add(node)
        logging.info('Added node %r to group %r', node, name)

    def remove_from_group(self, name, node):
        self._groups[name].remove(node)
        logging.info('Removed node %r from group %r', node, name)

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
