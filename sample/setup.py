
from reviewboard.extensions.packaging import setup
PACKAGE = "myextension"
VERSION = "0.1"


setup(
    name=PACKAGE,
    version=VERSION,
    description='Description of extension package.',
    author='Your Name',
    packages=['myextension'],
    entry_points={
        'reviewboard.extensions':
            '%s = myextension.myextension:SampleExtension1' % PACKAGE,
    },
)