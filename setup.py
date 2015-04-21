from setuptools import setup, find_packages
from codecs import open
from os import path

setup(
    name='spotty',

    version='0.0.1a2',

    description="Script for scraping the 'listentothis' subreddit and generating a Spotify playlist.",

    url='https://github.com/benjaminr/spotty',

    author='benjaminr',

    license='Apache',

    packages=['spotty'],

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Music',

        'License :: OSI Approved :: Apache',

        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ],

    keywords='music reddit spotify',

    install_requires=['pyspotify', 'praw', 'argparse'],

    entry_points={
        'console_scripts': [
            'spotty=spotty.spotty:main',
        ],
    },
)
