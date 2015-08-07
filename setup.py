#!/usr/bin/python3

from setuptools import setup, find_packages

from atxmon.version import __version__

setup(
	name = 'atxmond',
	version = __version__,
	options = {
		'build_exe': {
			'compressed': True,
			#'include_files': ['etc/atxmonc.conf', ]
		},
	},
	scripts = ['atxmond', ],
	packages = find_packages(),
)
