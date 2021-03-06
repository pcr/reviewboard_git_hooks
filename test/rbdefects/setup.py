from setuptools import setup, find_packages

PACKAGE="RB-Defects"
VERSION="0.1"

setup(
    name=PACKAGE,
    version=VERSION,
    description="""RB-Defects extension for Review Board""",
    author="Mike Conley",
    packages=["rbdefects"],
    entry_points={
        'reviewboard.extensions':
        '%s = rbdefects.extension:RBDefectsExtension' % PACKAGE,
    },
    package_data={
        'rbdefects': [
            'htdocs/css/*.css',
            'htdocs/js/*.js',
            'templates/rbdefects/*.html',
            'templates/rbdefects/*.txt',
        ],
    }
)


