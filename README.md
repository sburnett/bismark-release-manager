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
- Every *package* has an associated name, release, architecture, and version. To
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

Installation
------------

`brm` requires Python 2.7.

You can either run it directly from the git repository:

    python2.7 main.py releases list

or install it using pip:

    pip install --user .
    PATH="$PATH:~/.local/bin" brm releases list

Basic Options
-------------

You use the BISmark Release Manager through a command line tool called `brm`. By
default, `brm` stores all configuration information in `~/bismark-releases`. You
can change this with the `--root` flag. For example:

    brm --root=/data/users/bismark/releases releases list

If you encounter problems, it can be useful to enable more detailed logging
using the `--loglevel` flag. For example:

    brm --loglevel INFO deploy /data/users/bismark/downloads

Deployment Playbook
-------------------

### Deploying a New Release

First, prepare a new BISmark release using the OpenWRT buildroot and
`bismark-openwrt-overlay`.

Next, tell `bismark-release-manager` to manage the new release:

    brm releases new release_name /path/to/bismark/build

For example, to prepare a new release called *djelibeybi* you might run:

    brm releases new djelibeybi /data/users/bismark/builds/djelibeybi

where `/data/users/bismark/builds/djelibeybi` is an OpenWRT buildroot (*i.e.*,
contains a `.config`, `feeds.conf`, `build-bismark.sh`, etc.)

This will copy all packages and images from the release into
`~/bismark-releases/releases/djelibeybi/{packages,images}`. It will also make
note of which packages are built in to the image versus those packages available
as *extra* packages in
`~/bismark-releases/releases/djelibeybi/{builtin-packages,extra-packages}`.

Next, save your changes to version control using `brm commit`:

    brm commit

This will commit the files necessary to store a reproducible snapshot of your
release. It will prompt you to type a commit message.

To deploy the release use the `brm deploy` command:

    brm deploy /data/users/bismark/downloads

Note that this will deploy *all* releases, not just the *djelibeybi* release.
You must deploy it into an empty directory, so be sure to delete (or move) the
contents of `/data/users/bismark/downloads` before deploying the releases. After
deploying the releases, you can copy them to a Web server (*e.g.*,
`downloads.projectbismark.net`.)

### Creating New Groups

You can apply actions (*e.g.*, `brm packages upgrade`) on individual routers,
but it is often easier to create groups of routers. For example, to create a new
group of routers representing our development testbed:

    brm groups new testbed OW204E7F4A7478 OWC43DC79DE139
    brm groups add-nodes testbed OWC43DC7B0AE09 OWC43DC7B0AE63

You can list groups,

    brm groups list

list the contents of a group,

    brm groups list testbed

and list all groups and their contents:

    brm groups list-all

### Upgrading a Package

Suppose you discover a bug `bismark-mgmt` and want to fix it. Because
`bismark-mgmt` is a builtin package, you can upgrade it using `brm upgrade`.

First, build a new ipk file to fix the problem, making sure to increase the revision
and/or version number. For example, the *djelibeybi* release might ship with version
`HEAD-20` of `bismark-mgmt` and your fix could have version `HEAD-21`.

Next, import the upgraded package using `brm packages import`:

    brm packages import djelibeybi /data/users/bismark/builds/djelibeybi-updates/bin/ar71xx/packages/bismark-mgmt_HEAD-21_ar71xx.ipk

This will make a copy of the package in
`~/bismark-releases/releases/djelibeybi/packages`. If you attempt to import an
updated package without changing the version number, you will get an error.

Next you must tell `brm` that you wish to use that package as an upgrade on some
routers using the `brm packages upgrade` command. For example, to upgrade the
package on *all* routers running the *djelibeybi* release:

    brm packages upgrade djelibeybi ar71xx bismark_mgmt HEAD-21 default

The special keyword *default* refers to *all* routers in the deployment. It
is often not a good idea to push an upgrade to all routers without first testing
it. To push the upgrade to a small set of routers:

    brm packages upgrade djelibeybi ar71xx bismark_mgmt HEAD-21 testbed

Here, *testbed* refers to the group of routers we created earlier.

As before, run `brm commit` and `brm deploy` to deploy the changes to the router
deployment.

### Creating a New Experiment

Suppose you want to install an new measurement experiment called
*HappinessMonitor*, which tries to measure the general well-being of home
network users. You want to deploy it on a set of routers after they have been
deployed in the field.

First, build the packages necessary for this experiment. For example,
*HappinessMonitor* might need a package called `bismark-measure-happiness`. You
need to build the package for each release and architecture on which you want it
to run.

Next, create a new experiment:

    brm experiments new HappinessMonitor

This will prompt you to enter a display name for the experiment (*i.e.*, the
name that we will show to users) and a brief description of the experiment.

Next, import packages for each release:

    brm packages import djelibeybi /data/users/bismark/builds/djelibeybi-updates/bin/ar71xx/packages/bismark-measure-happiness_HEAD-1_ar71xx.ipk
    brm packages import quirm /data/users/bismark/builds/quirm-updates/bin/ar71xx/packages/bismark-measure-happiness_HEAD-1_ar71xx.ipk
    ...

Next, add packages to the experiment. Suppose we want to deploy this experiment
on a group of households in Atlanta:

    brm experiments add-package HappinessMonitor djelibeybi ar71xx bismark-measure-happiness HEAD-1 atlanta-routers
    brm experiments add-package HappinessMonitor quirm ar71xx bismark-measure-happiness HEAD-1 atlanta-routers
    ...

If *HappinessMonitor* contains additional packages or releases, repeat the
`import` and `add-package` process for each package and release.

By default, users must manually enable experiments using the LuCI Web interface.
If you want routers to install the experiment automatically:

    brm experiments install-by-default HappinessMonitor atlanta-routers

Going even further, if you want to prevent users from removing the experiment
from their router:

    brm experiments require HappinessMonitor atlanta-routers

As always, you must `brm commit` and `brm deploy` to make your changes visible
to the deployment.

### Revoking an Experiment

Suppose you discover a critical security vulnerability in *HappinessMonitor*
and want to disable it on all routers while you prepare a fix:

    brm experiments revoke HappinessMonitor atlanta-routers

All routers in the `atlanta-routers` group will remove the experiment the next
time they run `bismark-experiments-manager`, which happens every 12 hours.

Manually Editing Configurations
-------------------------------

It can be tedious to manage releases using the command line. Fortunately, it is
easy to edit *some* configuration files in the release. Here's a summary of the
directory structure of a sample releases directory (*e.g.*,
`~/bismark-releases`) with annotations of which files it is safe to edit by hand:

    experiments/                                       # All files in this directory are easy to edit by hand.
                HappinessMonitor/                      # One directory for each experiment.
                                 conflicts             # List of conflicting experiments.
                                 description           # A short description of the experiment.
                                 display-name          # The name to show the user (e.g., "BISmark Happiness Monitor")
                                 installed-by-default  # List of groups which should install by default. (Users can remove.)
                                 packages              # List of package groups, releases, names, versions and architectures
                                 required              # List of groups which *must* install the package. (Users cannot remove.)
                                 revoked               # List of groups which should revoke the experiment.
    groups/                 # All files in this directory are easy to edit by hand.
           atlanta-routers  # A list of routers in Atlanta, GA, one router name per line. You cannot nest groups.
           testbed          # A list of routers in the Klaus 3337 testbed.
    releases/                                   # Most files in this directory SHOULD NOT BE EDITED BY HAND.
             djelibeybi/                        # One directory per release.
                        images/
                               openwrt-bismark-djelibeybi-ar71xx-wndr3700-squashfs-factory.img
                               ...
                        packages/               # Set of packages available for deployment. Do not add files manually.
                                 507ec3edae8b603d30e808558ffb3e0acc3f6c83.ipk
                                 ...
                        architectures           # Do not edit.
                        builtin-packages        # Do not edit.
                        extra-packages          # List of packages in the "extra" set. You can edit this file.
                        fingerprinted-images    # Do not edit.
                        fingerprinted-packages  # Do not edit.
                        package-upgrades        # List of packages to upgrade. You can edit this file.
             quirm/
                        ...

Running `brm deploy` will check for errors in your edited configurations. Keep
in mind that the releases directory is a git repository, which can helpful for
recovering old release configurations in case you screw something up.
