#!/usr/bin/env python
from setuptools import find_packages, setup

REQUIRES = ["scrubadub", "in-place"]

setup(
    name="Obfuscator",
    version="1.0",
    url="https://github.com/bshakur8/obfuscator",
    author="Bhaa Shakur",
    author_email="bhaa.shakur@gmail.com",
    license="MIT",
    packages=find_packages("."),
    entry_points={"console_scripts": ["obfuscator=main:main"]},
    zip_safe=False,
    install_requires=REQUIRES,
)
