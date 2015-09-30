#!/usr/bin/python3

from setuptools import setup, find_packages

from atxmond.version import __version__

setup(
	name = 'atxmond',
	version = __version__,
	options = {
		'build_exe': {
			'compressed': True,
			#'include_files': ['etc/atxmonc.conf', ]
		},
	},
	#scripts = ['atxmond', ],
	entry_points = {'console_scripts': 'atxmond = atxmond:main'},
	packages = find_packages(),
	include_package_data = True,
)
