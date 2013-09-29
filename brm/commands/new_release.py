import errno
import glob
import hashlib
import os

from .. import opkg

def run(args):
    root_path = os.path.expanduser(args.root)
    build_root = os.path.expanduser(args.buildroot)

    if not os.path.isdir(root_path):
        return "releases root (%s) doesn't exist" % root_path
    if not is_openwrt_buildroot(build_root):
        return 'buildroot (%s) must be a compiled OpenWRT buildroot directory' % build_root

    release_path = os.path.join(root_path, args.name)
    if os.path.isdir(release_path):
        return 'release already exists'

    architectures = get_architectures(build_root)
    builtin_packages = get_builtin_packages(build_root)
    located_packages = locate_packages(build_root)

    os.makedirs(release_path)
    write_architectures(release_path, architectures)
    write_builtin_packages(release_path, builtin_packages)
    write_located_packages(release_path, located_packages)
    write_package_directories(release_path, build_root)

def is_openwrt_buildroot(build_root):
    if not os.path.isfile(os.path.join(build_root, '.config')):
        return False
    if not os.path.isdir(os.path.join(build_root, 'bin')):
        return False
    if not os.path.isdir(os.path.join(build_root, 'build_dir')):
        return False
    return True

def get_architectures(build_root):
    architectures = set()
    pattern = os.path.join(build_root, 'bin', '*')
    for filename in glob.iglob(pattern):
        if not os.path.isdir(filename):
            continue
        architecture = os.path.basename(filename)
        architectures.add(architecture)
    return architectures

def get_builtin_packages(build_root):
    packages = set()
    pattern = os.path.join(build_root, 'build_dir', 'target-*', 'root-*',
                           'usr', 'lib', 'opkg', 'info', '*.control')
    for filename in glob.iglob(pattern):
        package = opkg.parse_control_file(filename)
        if package.name is None:
            print 'skipping', filename, "because it's missing a name"
            continue
        if package.version is None:
            print 'skipping', filename, "because it's missing a version"
            continue
        if package.architecture is None:
            print 'skipping', filename, "because it's missing an architecture"
            continue
        packages.add(package)
    return packages

def get_images(build_root):
    images = []
    pattern = os.path.join(build_root, 'bin', '*', '*')
    for filename in glob.iglob(pattern):
        if os.path.isfile(filename):
            images.append(filename)
    return images

def get_package_fingerprint(filename):
    with open(filename) as handle:
        contents = handle.read()
    hasher = hashlib.sha1()
    hasher.update(contents)
    return hasher.hexdigest()

def locate_packages(build_root):
    located_packages = set()
    pattern = os.path.join(build_root, 'bin', '*', 'packages', '*.ipk')
    for filename in glob.iglob(pattern):
        package = opkg.parse_ipk(filename)
        sha1 = get_package_fingerprint(filename)
        located_package = opkg.LocatedPackage(
                name=package.name,
                version=package.version,
                architecture=package.architecture,
                sha1=sha1)
        located_packages.add(located_package)
    return located_packages

def write_builtin_packages(release_path, builtin_packages):
    builtin_packages_filename = os.path.join(release_path, 'builtin-packages')
    with open(builtin_packages_filename, 'w') as handle:
        for package in sorted(builtin_packages):
            print >>handle, package.name, package.version, package.architecture

def write_architectures(release_path, architectures):
    architectures_filename = os.path.join(release_path, 'architectures')
    with open(architectures_filename, 'w') as handle:
        for architecture in sorted(architectures):
            print >>handle, architecture

def write_located_packages(release_path, located_packages):
    located_packages_filename = os.path.join(release_path, 'located-packages')
    with open(located_packages_filename, 'w') as handle:
        for located_package in sorted(located_packages):
            print >>handle, located_package.name, located_package.version, located_package.architecture, located_package.sha1

def write_package_directories(release_path, build_root):
    package_directories_filename = os.path.join(release_path, 'package-directories')
    with open(package_directories_filename, 'w') as handle:
        pattern = os.path.join(build_root, 'bin', '*', 'packages')
        for path in glob.iglob(pattern):
            if not os.path.isdir(path):
                continue
            print >>handle, path
