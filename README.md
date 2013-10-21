BISmark Release Manager
=======================

This software manages collections of BISmark releases. It replaces
`scripts/deploy-release.sh` and `scripts/deploy-updates.sh` from the
`bismark-openwrt-overlay` repository and their associated configurations.
Unlike those scripts, `bismark-release-manager`:

- Manages *collections* of releases and can share configurations across releases
  as necessary. This means we can now deploy experiments across all firmware
  versions without copying experiment configurations between release
  directories.
- Operates on package *versions* and *fingerprints* rather than just package
  names. This means it is impossible to accidently upgrade package versions by
  simply building a new version; you must explicitly upgrade packages.
- Can upgrade packages on individual routers or small groups of routers. The
  previous system didn't automate this process, so you had to manually install
  updates on routers for testing prior to wider deployment.

Basic Concepts
--------------

Deploying a New Release
-----------------------

Upgrading a Package
-------------------

Creating a New Experiment
-------------------------

Revoking an Experiment
----------------------

