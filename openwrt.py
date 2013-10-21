import glob
import logging
import os

import opkg


class BuildTree(object):

    def __init__(self, build_root):
        logging.info('Checking whether "%s" is an OpenWrt build tree',
                     build_root)
        if not os.path.isfile(os.path.join(build_root, '.config')):
            raise Exception('OpenWrt build missing .config')
        if not os.path.isdir(os.path.join(build_root, 'bin')):
            raise Exception('OpenWrt build missing bin/')
        if not os.path.isdir(os.path.join(build_root, 'build_dir')):
            raise Exception('OpenWrt build mssing build_dir/')
        self._build_root = build_root

    def architectures(self):
        architectures = set()
        pattern = os.path.join(self._build_root, 'bin', '*')
        logging.info('Getting architectures from "%s"', pattern)
        for filename in glob.iglob(pattern):
            architecture = os.path.basename(filename)
            if not os.path.isdir(filename):
                logging.info('"%s" is not an architecture', architecture)
                continue
            logging.info('Adding architecture "%s"', architecture)
            architectures.add(architecture)
        return architectures

    def images(self):
        images = set()
        pattern = os.path.join(self._build_root, 'bin', '*', '*')
        logging.info('Getting images from "%s"', pattern)
        for filename in glob.iglob(pattern):
            if not os.path.isfile(filename):
                logging.info('"%s" is not an image', filename)
                continue
            logging.info('Adding image "%s"', filename)
            architecture = os.path.basename(os.path.dirname(filename))
            images.add((filename, architecture))
        return images

    def builtin_packages(self):
        packages = set()
        pattern = os.path.join(
            self._build_root, 'build_dir', 'target-*', 'root-*',
            'usr', 'lib', 'opkg', 'info', '*.control')
        logging.info('Getting builtin packages from "%s"', pattern)
        for filename in glob.iglob(pattern):
            package = opkg.parse_control_file(filename)
            if package is None:
                logging.warning('Skipping %s', filename)
                continue
            logging.info('Adding builtin package "%s"', filename)
            packages.add(package)
        return packages

    def package_directories(self):
        directories = set()
        pattern = os.path.join(self._build_root, 'bin', '*', 'packages')
        logging.info('Getting package directories from "%s"', pattern)
        for path in glob.iglob(pattern):
            if not os.path.isdir(path):
                logging.info('"%s" is not a package directory', path)
                continue
            logging.info('Adding package directory "%s"', path)
            directories.add(path)
        return directories
