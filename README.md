BISmark Release Manager
=======================

This software manages collections of BISmark releases. It replaces
`scripts/deploy-release.sh` and `scripts/deploy-updates.sh` from the
`bismark-openwrt-overlay` repository and their associated configurations.
Unlike those scripts, `bismark-release-manager`:

- Manages *collections* of releases (rather than each release individually) and
  can share configurations across releases when appropriate. This means we can
  now deploy experiments across all firmware versions without copying experiment
  configurations between release directories.
- Operates on package *versions* and *fingerprints* rather than just package
  names. This means it is now impossible to accidentally upgrade package
  versions by simply building a new package version; you must explicitly upgrade
  packages.
- Can upgrade packages on individual routers or small groups of routers. The
  previous system didn't automate this process, so you had to manually install
  updates on routers for testing prior to wider deployment.

Installation
------------

`brm` requires Python 2.7 and rsync.

You can either run it directly from the git repository:

    python2.7 main.py releases list

or install it using pip:

    pip install --user .
    PATH="$PATH:~/.local/bin" brm releases list

Basic Concepts
--------------

- The release manager works by making copies of all packages and images from
  each BISmark release and storing them in git. This means you must *import*
  packages and images before you can deploy them on
  `downloads.projectbismark.net`. Luckily, it's easy to import all packages and
  images from an OpenWRT build directory.
- A *release* is a version of the BISmark firmware and its associated packages.
  Examples of releases are the klatch, quirm, and lancre releases. During
  development, each release candidate is a new release (e.g., lancre-rc1,
  lancre-rc2, etc.) because each release candidate has a new firmware image with
  slightly different software.
- Every *package* has an associated release, architecture, name, and version. To
  avoid ambiguity, when working with packages, you must always specify all four
  parameters.
- Every release has a set of *builtin packages*, which are built in to the
  firmware itself. Every release also has a set of *extra packages*, which are
  *not* built in to the firmware; these are packages that advanced users can
  install manually using LuCI or opkg.
- An *upgrade* is a new version of a package that replaces one of the builtin
  packages for a release.
- A *group* is a set of BISmark routers. You can often use group identifiers
  instead of individual router names, for convenience. For example, a group
  named `testbed` could contain the router IDs for all routers located at
  Georgia Tech and you could use this group to quickly install experiments
  on those routers for testing.
- An *experiment* is a collection of packages that can be installed on routers
  in the field. Each experiment also has metadata about what it does (*e.g.*, a
  brief description of the experiment's purpose) and how it should be installed
  on routers (*e.g.*, whether it should be installed by default, whether the
  user can disable the experiment, etc.)

Useful Options
--------------

You use the BISmark Release Manager through a command line tool called `brm`. By
default, `brm` stores all configuration information in `~/bismark-releases`. You
can change this with the `--root` flag. For example:

    brm --root=/data/users/bismark/releases releases list

If you encounter problems, it can be useful to enable more detailed logging
using the `--loglevel` flag. For example:

    brm --loglevel INFO deploy
    
Tutorial
--------

[How to perform common deployment tasks](USAGE.md).
