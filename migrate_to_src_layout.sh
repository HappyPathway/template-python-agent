#!/bin/bash
# Script to migrate the project to a src layout

# Ensure src directory exists
mkdir -p src

# Move the ailf package to src
if [ -d "ailf" ]; then
    # First check if src/ailf already exists
    if [ -d "src/ailf" ]; then
        echo "src/ailf already exists. Please check and merge manually if needed."
    else
        echo "Moving ailf package to src directory..."
        mv ailf src/
        echo "Migration completed successfully."
    fi
else
    echo "ailf directory not found. Nothing to move."
fi

echo "Updating pyproject.toml for src layout..."
# Update the pyproject.toml file with the proper src layout configuration
# Note: The file already has some of these configurations, so we'll check first

# Handle the packages and where attributes - only if needed
if ! grep -q 'package-dir = {"" = "src"}' pyproject.toml; then
    sed -i 's/\[tool.setuptools\]/[tool.setuptools]\npackage-dir = {"" = "src"}/' pyproject.toml
fi

# Remove any explicit packages line that could conflict with find-packages
if grep -q 'packages = \["ailf"\]' pyproject.toml; then
    sed -i '/packages = \["ailf"\]/d' pyproject.toml
fi

# Make sure the exclude list includes pyutils and setup to avoid multiple packages error
if ! grep -q 'pyutils\*' pyproject.toml; then
    sed -i 's/exclude = \["tests\*", "examples\*", "docs\*"\]/exclude = \["tests\*", "examples\*", "docs\*", "pyutils\*", "setup\*", "utils\*"\]/' pyproject.toml
fi

# Fix license format to avoid deprecation warnings
if grep -q 'license = "MIT"' pyproject.toml; then
    sed -i 's/license = "MIT"/license = {text = "MIT"}/' pyproject.toml
fi

# Handle the pyutils and setup directories that are causing issues
echo "Creating __init__.py files in top-level directories to make them importable packages..."
mkdir -p pyutils
touch pyutils/__init__.py
mkdir -p setup
touch setup/__init__.py

# Check for src/ailf/__init__.py to ensure it's a proper package
if [ -d "src/ailf" ] && [ ! -f "src/ailf/__init__.py" ]; then
    echo "Creating __init__.py in src/ailf to make it a proper package..."
    touch src/ailf/__init__.py
fi

echo "Creating setup.py if it doesn't exist..."
if [ ! -f "setup.py" ] || ! grep -q "setuptools.setup()" setup.py; then
    cat > setup.py << 'EOF'
#!/usr/bin/env python3
"""
Setup script for the AILF package.
This is a minimal setup.py file that delegates to pyproject.toml.
"""

import setuptools

if __name__ == "__main__":
    setuptools.setup()
EOF
    chmod +x setup.py
    echo "Created setup.py file."
fi

echo "Checking if pip is available in user mode..."
if command -v pip &> /dev/null; then
    echo "Installing package in development mode using pip..."
    pip install -e . --user
else
    echo "WARNING: pip not found. Skipping installation."
    echo "You can install the package manually with: pip install -e ."
fi

echo "Migration to src layout completed successfully."
