#!/usr/bin/env python
"""
zumanji
=======

:copyright: (c) 2012 DISQUS
:license: Apache License 2.0, see LICENSE for more details.
"""

from setuptools import setup, find_packages

# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
try:
    __import__('multiprocessing')
except ImportError:
    pass

tests_require = [
    'django-nose',
    'mock',
    'nose',
]


install_requires = [
    'django>=1.2',
    'psycopg2',
    'django-crispy-forms>=1.1.4',
    'south',
]

setup(
    name='zumanji',
    version='0.2.7',
    author='DISQUS',
    author_email='opensource@disqus.com',
    url='https://github.com/disqus/zumanji',
    description='A web interface for aggregating results from nose-performance',
    long_description=__doc__,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite='runtests.runtests',
    license='Apache License 2.0',
    include_package_data=True,
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
