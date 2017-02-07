from setuptools import setup, find_packages


setup(
    name='dvhb-hybrid',
    version='0.0.4',
    description='',
    author='Malev A',
    author_email='am@dvhb.ru',
    url='https://git.dvhb.ru/devhub-libs/dvhb-hybrid',
    packages=find_packages(),
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Framework :: Django',
        'Framework :: Aiohttp',
    ],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'psycopg2',
        'aiopg',
        'aiohttp_apiset',
        'sqlalchemy',
        'invoke',
        'pyyaml',
    ]
)
