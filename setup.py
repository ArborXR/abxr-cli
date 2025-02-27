#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#
from setuptools import setup

setup(
    name = 'abxrcli',
    version = '0.9.1',
    packages = ['abxr'],
    entry_points = {
        'console_scripts': [
            'abxr-cli = abxr.cli:main',
        ]
    },
    install_requires = [
    ],
    include_package_data=True,
)
