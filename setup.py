#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import codecs
import os

from setuptools import find_packages, setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='aiotftp',
    version='0.0.1',
    author='Terry Kerr',
    author_email='terry@dtkerr.ca',
    maintainer='Terry Kerr',
    maintainer_email='terry@dtkerr.ca',
    packages=find_packages(),
    license='Mozilla Public License 2.0 (MPL 2.0)',
    description='Python 3.6+ asyncio TFTP server',
    long_description=read('README.md'),
    install_requires=[],
    tests_require=['pytest'],
    setup_requires=['setuptools>=17.1'],
    entry_points={
        'pytest11': [
            'aiotftp=aiotftp',
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
    ],
)
