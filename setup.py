#!/usr/bin/env python3
import os

from setuptools import find_packages, setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return open(file_path, encoding='utf-8').read()


setup(
    name='aiotftp',
    version='0.2.1',
    author='Terry Kerr',
    author_email='terry@dtkerr.ca',
    maintainer='Terry Kerr',
    maintainer_email='terry@dtkerr.ca',
    packages=find_packages(),
    license='Mozilla Public License 2.0 (MPL 2.0)',
    description='Python 3.5+ asyncio TFTP server',
    long_description=read('README.rst'),
    install_requires=[
        'attrs',
        'async-timeout'
    ],
    tests_require=[
        'async-generator',
        'hypothesis',
        'pytest',
        'pytest-asyncio'
    ],
    setup_requires=['setuptools>=17.1'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Framework :: AsyncIO',
    ],
)
