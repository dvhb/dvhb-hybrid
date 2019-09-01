import re
from pathlib import Path

from setuptools import setup, find_packages


with Path(__file__).with_name('dvhb_hybrid').joinpath('__init__.py').open() as f:
    VERSION = re.compile(r'.*__version__ = \'(.*?)\'', re.S).match(f.read()).group(1)

setup(
    name='dvhb-hybrid',
    version=VERSION,
    description='',
    author='Malev A',
    author_email='am@dvhb.ru',
    url='https://github.com/dvhb/dvhb-hybrid',
    packages=find_packages(),
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
        'Framework :: Django',
        'Framework :: Aiohttp',
    ],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'django',
        'psycopg2-binary',
        'aioredis>=1.0.0',
        'aioworkers',
        'aiohttp-apiset',
        'asyncpgsa',
        'aiohttp_apiset',
        'sqlalchemy',
        'pyyaml',
        'Pillow',
        'Babel',
        'aioauth-client',
    ]
)
