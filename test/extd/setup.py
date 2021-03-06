from setuptools import setup, find_packages

PACKAGE="Ext-D"
VERSION="0.1"

setup(
    name=PACKAGE,
    version=VERSION,
    description="""Ext-D extension for Review Board""",
    author="Mike Conley",
    packages=["extd"],
    entry_points={
        'reviewboard.extensions':
        '%s = extd.extension:ExtDExtension' % PACKAGE,
    },
    package_data={
        'extd': [
            'htdocs/css/*.css',
            'htdocs/js/*.js',
            'templates/extd/*.html',
            'templates/extd/*.txt',
        ],
    },
    install_requires=['Ext-C>=0.1']
)


