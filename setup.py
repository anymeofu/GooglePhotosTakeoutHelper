"""
Setup script for Google Photos Takeout Helper
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read README
readme_path = Path(__file__).parent / "../README_AI.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="google-photos-takeout-helper",
    version="4.1.0",
    author="Google Photos Takeout Helper Contributors",
    description="Tool to help organize Google Photos takeout exports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Xentraxx/GooglePhotosTakeoutHelper",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Graphics",
        "Topic :: System :: Archiving",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "gui": ["customtkinter>=5.2.0"],
        "dev": ["pytest>=7.0.0", "black>=22.0.0", "flake8>=5.0.0"],
    },
    entry_points={
        "console_scripts": [
            "gpth=cli.gpth_cli:cli",
            "gpth-gui=gui.gpth_gui:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)