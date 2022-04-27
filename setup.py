from setuptools import setup, find_packages
import re

modcontents = open('omaya/__init__.py').read()
version = re.search(r"__version__ = '([^']*)'",modcontents).group(1)

setup(
    name='omaya',
    version=version,
    description='OMAyA Monitor and Control',
    author='Gopal Narayanan',
    author_email='gopal@astro.umass.edu',
    install_requires=['numpy', 'matplotlib', 'pandas'],
    packages=['omaya'],
    #scripts=[]
)
