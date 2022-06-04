import re
from pathlib import Path

from setuptools import find_packages, setup


def __read_version():
    with Path(__file__).with_name('dvhb_hybrid').joinpath('__init__.py').open() as f:
        matches = re.compile(r'.*__version__ = \'(.*?)\'', re.S).match(f.read())
        if not matches:
            raise ValueError('Could not find version')
        return matches.group(1)


extras_require = {
    'model-translation': ['django-modeltranslation>=0.18'],
    'mptt': ['django-mptt>=0.13'],
    'redis': ['redis>=4.3']
}


setup(
    name='dvhb-hybrid',
    version=__read_version(),
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
        'Babel>=2.10',
        'Django>=4.0',
        'Jinja2>=3.1',
        'SQLAlchemy>=1.3,<1.4',
        'Pillow>=9.1',
        'PyYAML<6.0',  # TODO: upgrade
        'aioauth-client>=0.27',
        'aiohttp>=3.8',
        'aiohttp_jinja2>=1.5',
        'aiohttp-apiset>=0.9',
        'aioworkers>=0.20',
        'asyncpgsa>=0.27',
        'attrs>=21.4',
        'django-imagekit>=4.1',
        'openpyxl>=3.0',
        'pilkit>=2.0',
        'psycopg2-binary>=2.9',
        'pytest>=7.1',
        'python-jose>=3.3',
        'yarl>=1.7'
    ],
    extras_require={
        'all': sum([i for i in extras_require.values()], []),
        **extras_require
    }
)
