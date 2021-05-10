# -*- coding: utf-8 -*-
"""qiskit-runtime

Package of tools for using the Qiskit-runtime.
"""

import os
import sys
import subprocess
import setuptools


MAJOR = 0
MINOR = 1
MICRO = 0

ISRELEASED = False
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)

REQUIREMENTS = [
                'qiskit-terra>=0.17',
                'qiskit-ibmq-provider>=0.12'
               ]
PACKAGES = setuptools.find_packages()
PACKAGE_DATA = {}
DOCLINES = __doc__.split('\n')
DESCRIPTION = DOCLINES[0]
LONG_DESCRIPTION = "\n".join(DOCLINES[2:])

def git_short_hash():
    try:
        git_str = "+" + os.popen('git log -1 --format="%h"').read().strip()
    except:  # pylint: disable=bare-except
        git_str = ""
    else:
        if git_str == '+': #fixes setuptools PEP issues with versioning
            git_str = ''
    return git_str

FULLVERSION = VERSION
if not ISRELEASED:
    FULLVERSION += '.dev'+str(MICRO)+git_short_hash()

local_path = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(local_path)
sys.path.insert(0, local_path)
sys.path.insert(0, os.path.join(local_path, 'qiskit_runtime'))  # to retrive _version

def write_version_py(filename='qiskit_runtime/version.py'):
    cnt = """\
# THIS FILE IS GENERATED FROM QISKIT_RUNTIME SETUP.PY
# pylint: disable=missing-module-docstring,invalid-name
short_version = "%(version)s"
version = "%(fullversion)s"
release = %(isrelease)s
"""
    a = open(filename, 'w')
    try:
        a.write(cnt % {'version': VERSION, 'fullversion':
                       FULLVERSION, 'isrelease': str(ISRELEASED)})
    finally:
        a.close()

# always rewrite _version
if os.path.exists('qiskit_runtime/version.py'):
    os.remove('qiskit_runtime/version.py')
# write the version info
write_version_py()

setuptools.setup(
    name='qiskit-runtime',
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=PACKAGES,
    url="",
    author="Qiskit Development Team",
    author_email="hello@qiskit.org",
    license="Apache 2.0",
    classifiers=[
        "Environment :: Web Environment",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering",
    ],
    package_data=PACKAGE_DATA,
    install_requires=REQUIREMENTS,
    zip_safe=False
)
