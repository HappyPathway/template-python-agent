#!/usr/bin/env bash
# filepath: /workspaces/template-python-dev/dev_setup.sh

# Exit on error
set -e

# Check Python version
python_version=$(python --version 2>&1 | sed 's/Python //')
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [ "$python_major" -lt 3 ] || [ "$python_major" -eq 3 -a "$python_minor" -lt 12 ]; then
    echo "Error: This project requires Python 3.12 or higher"
    echo "Current version: $python_version"
    exit 1
fi

echo "Python version $python_version is compatible"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the package in development mode with all extras
echo "Installing ailf package in development mode with all extras..."
pip install -e ".[all,dev]"

echo -e "\nDevelopment environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
