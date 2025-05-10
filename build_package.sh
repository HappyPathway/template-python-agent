#!/usr/bin/env bash
# filepath: /workspaces/template-python-dev/build_package.sh

# Exit on error
set -e

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info

# Ensure build tools are installed
echo "Installing build tools..."
pip install --upgrade pip build twine

# Build the package
echo "Building package..."
python -m build

# Show the built files
echo -e "\nBuild complete! Package files:"
ls -l dist/

echo -e "\nTo upload to PyPI, run:"
echo "python -m twine upload dist/*"

echo -e "\nTo install from the built package:"
echo "pip install dist/*.whl"
