#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=7.0', ]

test_requirements = [ ]

setup(
    author="Matin Nuhamunada",
    author_email='matinnu@biosustain.dtu.dk',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="A snakemake and snakedeploy wrapper for BGCFlow.",
    entry_points={
        'console_scripts': [
            'bgcflow_wrapper=bgcflow_wrapper.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='bgcflow_wrapper',
    name='bgcflow_wrapper',
    packages=find_packages(include=['bgcflow_wrapper', 'bgcflow_wrapper.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/matinnuhamunada/bgcflow_wrapper',
    version='0.1.0',
    zip_safe=False,
)
