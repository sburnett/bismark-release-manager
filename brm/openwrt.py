import glob
import os

import opkg

class BuildTree(object):
    def __init__(self, build_root):
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
        for filename in glob.iglob(pattern):
            if not os.path.isdir(filename):
                continue
            architecture = os.path.basename(filename)
            architectures.add(architecture)
        return architectures

    def images(self):
        images = set()
        pattern = os.path.join(self._build_root, 'bin', '*', '*')
        for filename in glob.iglob(pattern):
            if os.path.isfile(filename):
                images.add(filename)
        return images

    def builtin_packages(self):
        packages = set()
        pattern = os.path.join(self._build_root, 'build_dir', 'target-*', 'root-*',
                               'usr', 'lib', 'opkg', 'info', '*.control')
        for filename in glob.iglob(pattern):
            package = opkg.parse_control_file(filename)
            if package is None:
                logging.warning('Skipping %s', filename)
                continue
            packages.add(package)
        return packages

    def package_directories(self):
        directories = set()
        pattern = os.path.join(self._build_root, 'bin', '*', 'packages')
        for path in glob.iglob(pattern):
            if not os.path.isdir(path):
                continue
            directories.add(path)
        return directories
