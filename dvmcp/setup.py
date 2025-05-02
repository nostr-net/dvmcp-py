import os
from setuptools import setup, find_packages

# Read version from version.py
with open(os.path.join("dvmcp", "version.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "0.1.0"

# Read long description from README.md
with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="dvmcp",
    version=version,
    description="Python implementation of the DVMCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Aljaz Ceru",
    author_email="aljaz@ceru.si",
    url="https://github.com/nostr-net/dvmcp-py",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "nostr-sdk>=0.1.0",
        "jsonschema>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "mypy>=0.9.0",
        ],
        "resources": [
            "psutil>=5.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dvmcp-provider=dvmcp.cli.provider:main",
            "dvmcp-client=dvmcp.cli.client:main",
        ],
    },
)