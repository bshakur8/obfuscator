#!/usr/bin/env python
from setuptools import setup, find_packages

REQUIRES = ["scrubadub==1.2.1", "in-place==0.4.0"]


setup(
    name="Obfuscator",
    version="0.1",
    url="https://github.com/bshakur8/obfuscator",
    author="Bhaa Shakur",
    author_email="bhaa.shakur@gmail.com",
    license="MIT",
    packages=find_packages("."),
    entry_points={"console_scripts": ["obfuscator=obfuscator.main:main"]},
    install_requires=REQUIRES,
)
