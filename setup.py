# -*- coding: utf-8 -*-
"""
Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>

License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt
"""
# Third party
from setuptools import setup


def load(fname):
    result = []
    with open(fname, "r") as file_:
        result = [package.strip() for package in file_.readlines()]
    return result


def setup_package():
    setup(use_scm_version=True, install_requires=load("requirements.txt"))


if __name__ == "__main__":
    setup_package()
