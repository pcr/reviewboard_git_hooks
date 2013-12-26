#import versiontools

from setuptools import setup, find_packages
import distutils.dir_util
import sys, os

name='reviewboard-git-hooks'
version = '0.0.1'

if sys.version <= '2.5':
    requires = ['simplejson']
else:
    requires = []

def get_os_log_dir():
  platform = sys.platform
  if platform.startswith('win'):
    try:
      return os.environ['APPDATA']
    except KeyError:
      print >>sys.stderr, 'Unspported operation system:%s'%platform
      sys.exit(1)
  return '/var/log'

def get_os_conf_dir():
  platform = sys.platform
  if platform.startswith('win'):
    try:
      return os.environ['ALLUSERSPROFILE']
    except KeyError:
      print 'Unspported operation system:%s'%platform
      sys.exit(1)
  return '/etc'

def mk_conf_path():
  directory = get_os_conf_dir()
  path = os.path.join(directory, name)
  distutils.dir_util.mkpath(path)
  return path

def mk_log_path():
  directory = get_os_log_dir()
  path = os.path.join(directory, name)
  distutils.dir_util.mkpath(path)
  return path

def after_install():
  mk_log_path()
  conf_path = mk_conf_path()
  distutils.file_util.copy_file('conf_templates/conf.ini', conf_path)

setup(name=name,
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='reviewboard git hook',
      author='PCR',
      author_email='pcrxjxj@gmail.com',
      url='http://code.google.com/p/reviewboard-git-hooks/',
      license='mit',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ] + requires,
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      init_used_rid_db = reviewboardgithooks.init_used_rid_db:main
      git-check-reviewboard = reviewboardgithooks.strict_review:main
      """,
      )

after_install()

