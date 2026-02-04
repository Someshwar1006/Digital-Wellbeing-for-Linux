#!/usr/bin/env python3
"""
Setup script for ZenScreen.

This is a fallback for systems that don't support pyproject.toml.
Prefer using: pip install .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="zenscreen",
    version="1.0.0",
    description="A Digital Wellbeing & Screen Time Tracker for Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="someshwar",
    author_email="someshwar@example.com",
    url="https://github.com/someshwar/zenscreen",
    license="GPL-3.0-or-later",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "pycairo>=1.20.0",
        "PyGObject>=3.42.0",
        "pynput>=1.7.6",
        "python-xlib>=0.33",
        "dbus-python>=1.3.2",
        "matplotlib>=3.7.0",
        "appdirs>=1.4.4",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "zenscreen=zenscreen.cli.main:main",
            "zenscreen-daemon=zenscreen.daemon.service:main",
        ],
        "gui_scripts": [
            "zenscreen-gtk=zenscreen.gui.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Desktop Environment :: Gnome",
        "Topic :: System :: Monitoring",
    ],
    keywords="screen-time digital-wellbeing productivity focus linux gtk",
    project_urls={
        "Bug Reports": "https://github.com/someshwar/zenscreen/issues",
        "Source": "https://github.com/someshwar/zenscreen",
        "Documentation": "https://github.com/someshwar/zenscreen#readme",
    },
)
