from setuptools import setup, find_packages

PACKAGE = "setssh"
VERSION = "0.1"

setup(
    name=PACKAGE,
    version=VERSION,
    description="Set ssh-rsa",
    author="Qingyong Zhang",
    packages=["setssh"],
    entry_points={
        'reviewboard.extensions':'setssh = setssh.extension:SetsshExtension',
    },
    package_data={
        'setssh_extension': ['/setssh/templates/*.html',],
    },
)