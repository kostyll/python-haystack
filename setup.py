#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setuptools scripts."""

from setuptools import setup

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2012 Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__status__ = "Production"

setup(name="haystack",
    version="0.17",
    description="Search C Structures in a process' memory",
    long_description=open("README.rst").read(),

    url="http://packages.python.org/haystack/",
    download_url="http://github.com/trolldbois/python-haystack/tree/master",
    license="GPL",
    classifiers=[
        "Topic :: System :: Networking",
        "Topic :: Security",
        "Environment :: Console",
        "Environment :: X11 Applications :: Qt",        
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
    ],
    keywords=["memory","analysis","forensics","struct","ptrace","reverse","heap"],
    author="Loic Jaquemet",
    author_email="loic.jaquemet+python@gmail.com",
    packages = ["haystack", "haystack.gui", "haystack.reverse", "haystack.reverse.libc", "haystack.reverse.win32"],
    #package_dir={"haystack.reverse": 'haystack/reverse'},
    package_data={"haystack.reverse": ['data/words.100'], },
    scripts = ["scripts/haystack", "scripts/haystack-gui", "scripts/haystack-dump", "scripts/haystack-reverse"],
    # use pip requirements.txt instead
    #install_requires = ["python-ptrace", "argparse", "networkx"],#"python-levenschtein", "python-networkx"],
    # build_tests_requires = ["python-ctypeslib","libqt-dev"]
    test_suite= "test.alltests",
    #tests_require="haystack",
    #entry_points = {'haystack.plugins':['haystack.model:register']},
)


