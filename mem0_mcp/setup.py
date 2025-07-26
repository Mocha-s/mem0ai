"""
Setup script for Mem0 MCP Server
"""

import os
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="mem0-mcp-server",
    version="1.0.0",
    description="Model Context Protocol server for Mem0",
    long_description=open("docs/README.md").read() if os.path.exists("docs/README.md") else "",
    long_description_content_type="text/markdown",
    author="Mem0 Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mem0-mcp-server=src.server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)