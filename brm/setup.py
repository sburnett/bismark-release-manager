from setuptools import setup

setup(
        name='bismark-release-manager',
        description='Manage releases, packages, experiments and upgrades '
                    'for the BISmark deployment.',
        license='MIT License',
        author='Sam Burnett',
        py_modules=[
            'commands',
            'common',
            'deploy',
            'experiments',
            'groups',
            'main',
            'openwrt',
            'opkg',
            'release',
            'tree',
        ],
        entry_points={'console_scripts': ['brm = main:main']},
    )
