#
#  setup.py
#  gw2-discord-webhooks
#
#  Copyright (c) 2020 Patrick "p2k" Schneider
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#

import os
from setuptools import find_packages, setup

script_path = os.path.dirname(__file__)

with open(os.path.join(script_path, "README.md")) as readme:
    README = readme.read()

with open(os.path.join(script_path, "requirements.txt")) as requirements:
    install_requires = []
    for line in requirements:
        install_requires.append(line.strip())

setup(
    name="gw2-discord-webhooks",
    version="0.1.0",
    packages=find_packages(),
    license="MIT License",
    description="Discord Webhooks for Guild Wars 2",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/p2k/gw2-discord-webhooks",
    install_requires=install_requires,
    author='Patrick "p2k" Schneider',
    author_email="me@p2k-network.org",
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    entry_points={"console_scripts": ["post_gw2_matches=gw2_discord_webhooks.matches:main",],},
)
