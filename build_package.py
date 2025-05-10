"""Build AILF Package Script

This script prepares the AILF package for distribution. It creates both source and wheel
distributions that can be installed via pip.
"""

import os
import re
import sys
import shutil
import subprocess
from setuptools import setup, find_packages

# Read version from __init__.py
with open('ailf/__init__.py', 'r') as f:
    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]*)['\"]", f.read())
    version = version_match.group(1) if version_match else '0.1.0'

setup(
    name="ailf",
    version=version,
    description="AI Liberation Front - A toolkit for building autonomous AI agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="AILF Team",
    author_email="info@ailf.dev",
    url="https://github.com/ailf-dev/template-python-dev",
    packages=find_packages(exclude=["tests*", "examples*"]),
    python_requires=">=3.12",
    include_package_data=True,
    install_requires=[
        "pydantic>=2.0.0",
        "pyzmq>=24.0.0",
        "redis>=5.0.0",
    ],
    extras_require={
        "ai": ["openai>=1.0.0", "anthropic>=0.3.0", "google-generativeai>=0.2.0"],
        "cloud": ["google-cloud-storage>=2.0.0", "google-cloud-secret-manager>=2.0.0"],
        "zmq": ["pyzmq>=24.0.0"],
        "redis": ["redis>=5.0.0", "async-timeout>=4.0.3"],
        "mcp": ["fastapi>=0.100.0", "uvicorn>=0.22.0"],
        "dev": [
            "pytest>=7.0.0", 
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0"
        ],
        "all": [
            "openai>=1.0.0", "anthropic>=0.3.0", "google-generativeai>=0.2.0",
            "google-cloud-storage>=2.0.0", "google-cloud-secret-manager>=2.0.0",
            "pyzmq>=24.0.0", "redis>=5.0.0", "async-timeout>=4.0.3",
            "fastapi>=0.100.0", "uvicorn>=0.22.0"
        ]tribution by:
1. Creating necessary directory structure
2. Generating or updating setup.py
3. Adding README.md and other metadata
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


# Package metadata
PACKAGE_NAME = "ailf"
VERSION = "0.1.0"
DESCRIPTION = "AI Liberation Front - Tools for building autonomous AI agents"
AUTHOR = "Your Name"
AUTHOR_EMAIL = "your.email@example.com"
URL = "https://github.com/yourusername/ailf"
CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3 :: Only",
    "Topic :: Software Development :: Libraries",
]


def ensure_directory(path):
    """Ensure a directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f"✓ Created directory: {path}")


def create_setup_py():
    """Create or update the setup.py file."""
    setup_py = f"""
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="{PACKAGE_NAME}",
    version="{VERSION}",
    author="{AUTHOR}",
    author_email="{AUTHOR_EMAIL}",
    description="{DESCRIPTION}",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="{URL}",
    project_urls={{
        "Bug Tracker": "{URL}/issues",
    }},
    classifiers={CLASSIFIERS},
    packages=setuptools.find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "pydantic>=2.0.0",
        "pyzmq>=24.0.0",
        "redis>=5.0.0",
    ],
    extras_require={{
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
        ]
    }}
)
"""
    with open("setup.py", "w") as f:
        f.write(setup_py)
    print("✓ Created setup.py")


def create_readme():
    """Create README.md file."""
    readme = f"""# {PACKAGE_NAME.upper()} - AI Liberation Front

{DESCRIPTION}

## Installation

```bash
pip install {PACKAGE_NAME}
```

## Features

- **ZMQ Messaging**: Distributed messaging patterns with ZeroMQ
- **Redis Integration**: Redis-based messaging and caching
- **AI Engine**: Unified interface to LLM providers
- **Structured I/O**: Pydantic models for type-safe interactions
- **Tool Management**: Register and manage agent tools
- **Storage**: Local and cloud storage integration
- **Monitoring**: Instrumentation for tracking agent behavior

## Quick Start

### ZMQ Messaging Example

```python
from ailf import DeviceManager, ZMQPublisher, ZMQSubscriber

# Create a forwarder device (PUB-SUB)
manager = DeviceManager()
device = manager.create_forwarder("tcp://*:5555", "tcp://*:5556")
device.start()

# Create a publisher
publisher = ZMQPublisher()
publisher.connect("tcp://localhost:5555")
publisher.publish("topic", "Hello, World!")

# Create a subscriber
subscriber = ZMQSubscriber()
subscriber.connect("tcp://localhost:5556")
subscriber.subscribe("topic")
subscriber.set_message_handler(lambda msg: print(f"Received: {{msg}}"))
subscriber.start_receiving()
```

### Redis Messaging Example

```python
from ailf import RedisClient, RedisPubSub

# Basic Redis operations
client = RedisClient()
client.set("key", "value")
value = client.get("key")

# PubSub messaging
pubsub = RedisPubSub()
pubsub.publish("channel", {"message": "Hello from AILF!"})

# Subscriber
def handle_message(data):
    print(f"Received: {{data}}")

subscriber = RedisPubSub()
subscriber.subscribe("channel", handle_message)
subscriber.run_in_thread()
```

## License

MIT License
"""
    with open("README.md", "w") as f:
        f.write(readme)
    print("✓ Created README.md")


def create_manifest():
    """Create MANIFEST.in file."""
    manifest = """include README.md
include LICENSE
"""
    with open("MANIFEST.in", "w") as f:
        f.write(manifest)
    print("✓ Created MANIFEST.in")


def main():
    """Main function to build the package."""
    print("Building AILF package...")
    
    # Create README and setup files
    create_readme()
    create_setup_py()
    create_manifest()
    
    print("\nBuilding package...")
    subprocess.run([sys.executable, "setup.py", "sdist", "bdist_wheel"])
    print("\n✓ Package build complete!")
    
    print("\nTo install the development version:")
    print("    pip install -e .\n")
    print("To install the built package:")
    print("    pip install dist/*.whl\n")
    print("To upload to PyPI (if you have credentials):")
    print("    pip install twine")
    print("    twine upload dist/*\n")


if __name__ == "__main__":
    main()
