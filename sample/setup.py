from setuptools import setup

PACKAGE = "extension"
VERSION = "0.1"


setup(
    name=PACKAGE,
    version=VERSION,
    description='Description of extension package.',
    author='Your Name',
    packages=['extension'],
    entry_points={
        'reviewboard.extensions':
            '%s = extension.extension:SampleExtension' % PACKAGE,
    },
)