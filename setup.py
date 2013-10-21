from setuptools import setup

setup(
        name='bismark-release-manager',
        version='1.0.1',
        description='Manage releases, packages, experiments and upgrades '
                    'for the BISmark deployment.',
        license='MIT License',
        author='Sam Burnett',
        py_modules=[
            'common',
            'deploy',
            'experiments',
            'groups',
            'main',
            'openwrt',
            'opkg',
            'release',
            'subcommands',
            'tree',
        ],
        entry_points={'console_scripts': ['brm = main:main']},
    )
