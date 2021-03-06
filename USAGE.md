Deployment Playbook
===================

Deploying a New Release
-----------------------

First, prepare a new BISmark release using
[bismark-openwrt-overlay](https://github.com/projectbismark/bismark-openwrt-overlay).

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

    brm deploy

Note that this will deploy *all* releases to
http://downloads.projectbismark.net, not just the *djelibeybi* release. The
script will deploy to a staging directory in `/tmp`, show you a diff between the
staging directory and the destination, then ask you whether you want to proceed
with deployment.


Creating New Groups
-------------------

You can apply actions (*e.g.*, `brm packages upgrade`) on individual routers,
but it's often easier to create groups of routers. For example, to create a new
group of routers representing our development testbed:

    brm groups new testbed OW204E7F4A7478 OWC43DC79DE139
    brm groups add-nodes testbed OWC43DC7B0AE09 OWC43DC7B0AE63

You can list groups,

    brm groups list

list the contents of a group,

    brm groups list testbed

and list all groups and their contents together:

    brm groups list-all

Upgrading a Package
-------------------

Suppose you discover a bug in the `bismark-mgmt` package and want to fix it.
Because `bismark-mgmt` is a builtin package, you can upgrade it using `brm
packages upgrade`.

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

    brm packages upgrade default djelibeybi ar71xx bismark_mgmt HEAD-21

The special keyword *default* refers to *all* routers in the deployment. It
is often not a good idea to push an upgrade to all routers without first testing
it. To push the upgrade to a small set of routers:

    brm packages upgrade testbed djelibeybi ar71xx bismark_mgmt HEAD-21

Here, *testbed* refers to the group of routers we created earlier.

As before, run `brm commit` and `brm deploy` to deploy the changes to the router
deployment.

Creating a New Experiment
-------------------------

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

    brm experiments add-package HappinessMonitor atlanta-routers djelibeybi ar71xx bismark-measure-happiness HEAD-1
    brm experiments add-package HappinessMonitor atlanta-routers quirm ar71xx bismark-measure-happiness HEAD-1
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

Revoking an Experiment
----------------------

Suppose you discover a critical security vulnerability in *HappinessMonitor*
and want to disable it on all routers while you prepare a fix:

    brm experiments revoke HappinessMonitor atlanta-routers

All routers in the `atlanta-routers` group will remove the experiment the next
time they run `bismark-experiments-manager`, which happens every 12 hours.

Manually Editing Configurations
===============================

It can be tedious to manage releases using the command line. Fortunately, it is
easy to edit *some* configuration files in the release. Here's a summary of the
directory structure of a sample releases directory (*e.g.*,
`~/bismark-releases`) with annotations of which files are safe to edit by hand:

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
