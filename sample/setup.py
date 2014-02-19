from setuptools import setup


PACKAGE = "sample"
VERSION = "0.1"


setup(
    name=PACKAGE,
    version=VERSION,
    description='Description of extension package.',
    author='Your Name',
    packages=['sample'],
    entry_points={
        'reviewboard.extensions':
            '%s = sample.extension:SampleExtension' % PACKAGE,
    },
)