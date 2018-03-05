from setuptools import setup, find_packages

from radiusauth import VERSION

setup(
    name='django-radius',
    author='Rob Golding',
    author_email='rob@robgolding.com',
    description='Django authentication backend for RADIUS',
    version=VERSION,
    license='BSD',
    url='http://robgolding63.github.com/django-radius/',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    zip_safe=False,
    packages=find_packages(),
    install_requires=['pyrad >= 1.2', 'future==0.16.0'],
)
