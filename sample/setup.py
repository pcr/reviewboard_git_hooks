from setuptools import setup


PACKAGE = "sample_extension"
VERSION = "0.1"


setup(
    name=PACKAGE,
    version=VERSION,
    description='Description of extension package.',
    author='Your Name',
    packages=['sample_extension'],
    entry_points={
        'reviewboard.extensions':
            '%s = sample_extension.extension:SampleExtension' % PACKAGE,
    },
)