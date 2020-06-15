import glob
import imp
import io
import os
from os import path
import re
import sys
import platform

from setuptools import Extension, find_packages, setup

PLATFORM_WINDOWS = (platform.system() == 'Windows')
PLATFORM_MACOSX = (platform.system() == 'Darwin')

MYDIR = path.abspath(os.path.dirname(__file__))

VERSION = imp.load_source('version', path.join('.', 'hookhub', 'version.py'))
VERSION = VERSION.__version__

# NOTE(kgriffs): python-mimeparse is better-maintained fork of mimeparse
REQUIRES = ['aiohttp',
            'pyzmq',
            'click',
            ]

try:
    sys.pypy_version_info
    PYPY = True
except AttributeError:
    PYPY = False

if PYPY:
    CYTHON = False
else:
    try:
        from Cython.Distutils import build_ext
        CYTHON = True
    except ImportError:
        # TODO(kgriffs): pip now ignores all output, so the user
        # may not see this message. See also:
        #
        #   https://github.com/pypa/pip/issues/2732
        #
        print('\nNOTE: Cython not installed. '
              'pitayah5 will still work fine, but may run '
              'a bit slower.\n')
        CYTHON = False

if CYTHON:
    if PLATFORM_WINDOWS:
        compile_args = []
    else:
        compile_args = ['-fno-strict-aliasing', '-D__STDC_LIMIT_MACROS', '-D__STDC_CONSTANT_MACROS']
    if not PLATFORM_MACOSX:
        compile_args.append('-std=c99')
    if 'DEBUG' in os.environ:
        compile_args.extend(['-O0', '-g'])
    else:
        compile_args.append('-O3')
    if 'ARCHI' in os.environ:
        compile_args.extend(['-march=%s' % os.environ['ARCHI']])
    else:
        compile_args.append('-march=native')

    def list_modules(dirname):
        pypath = glob.glob(path.join(dirname, '*.py'))
        pyxpath = glob.glob(path.join(dirname, '*.pyx'))
        filenames = pypath + pyxpath

        module_names = []
        for name in filenames:
            module, ext = path.splitext(path.basename(name))
            if module != '__init__':
                module_names.append((module, ext))

        return module_names
    package_names = ['hookhub']
    ext_modules = [
        Extension(
            package + '.' + module[0],
            sources=[path.join(*(package.split('.') + [module[0] + module[1]]))],
            extra_compile_args=compile_args
        )
        for package in package_names
        for module in list_modules(path.join(MYDIR, *package.split('.')))
    ]

    cmdclass = {'build_ext': build_ext}

else:
    cmdclass = {}
    ext_modules = []


def load_description():
    in_raw = False

    description_lines = []

    # NOTE(kgriffs): PyPI does not support the raw directive
    for readme_line in io.open('README.rst', 'r', encoding='utf-8'):
        if readme_line.startswith('.. raw::'):
            in_raw = True
        elif in_raw:
            if readme_line and not re.match('\s', readme_line):
                in_raw = False

        if not in_raw:
            description_lines.append(readme_line)

    return ''.join(description_lines)


setup(
    name='hookhub',
    version=VERSION,
    description='webhoo forward to local network',
    long_description=load_description(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Topic :: Database async writer',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='webhook',
    author='sunzhaoping',
    author_email='sunzhaoping@gmail.com',
    license='MIT License',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.7',
    install_requires=REQUIRES,
    cmdclass=cmdclass,
    ext_modules=ext_modules,
    entry_points={
        'console_scripts': [
            'hhserver = hookhub.server:main',
            'hhclient = hookhub.client:main',
        ]
    }
)
