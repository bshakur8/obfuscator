#!/usr/bin/env python
from setuptools import setup, find_packages

REQUIRES = ['scrubadub==1.2.1',
            'in-place==0.4.0']

setup(
    name='Obfuscator',
    version='0.1',
    url='https://git.vastdata.com/dev/orion/',
    author='VAST data MGMT-APP team',
    author_email='bhaa@vastdata.com',
    license='Copyright (C) Vast Data Ltd.',
    packages=find_packages('.'),
    entry_points={'console_scripts': ['obfuscator=obfuscator.main:main']},
    zip_safe=False,
    install_requires=REQUIRES
)
