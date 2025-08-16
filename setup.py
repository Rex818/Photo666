#!/usr/bin/env python3
"""
Setup script for PyPhotoManager.
"""

from setuptools import setup, find_packages
import os
import re

# Read version from package __init__.py
with open(os.path.join('src', 'picman', '__init__.py'), 'r', encoding='utf-8') as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        version = '0.1.0'

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="pyphoto-manager",
    version=version,
    author="PyPhotoManager Team",
    author_email="info@pyphoto-manager.org",
    description="Professional Photo Management Software",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pyphoto-manager/pyphoto-manager",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics :: Viewers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pyphoto-manager=picman.gui.main_window:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)