#!/usr/bin/env python3
"""Build script for ailf package.

This script builds both source and wheel distributions using Python's build module.
"""
import os
import shutil
import subprocess
import sys

def clean_dist():
    """Clean the dist directory before building."""
    if os.path.exists("dist"):
        print(f"Cleaning dist directory...")
        shutil.rmtree("dist")
        
    if os.path.exists("ailf.egg-info"):
        print(f"Cleaning egg-info directory...")
        shutil.rmtree("ailf.egg-info")
        
    print("Clean completed.")

def build_package():
    """Build the package using Python's build module."""
    print("Building source and wheel distributions...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "build"])
    subprocess.check_call([sys.executable, "-m", "build"])
    print("Build completed. Distribution files are in the 'dist' directory.")

def list_dist():
    """List the distribution files."""
    print("\nGenerated distribution files:")
    if os.path.exists("dist"):
        files = os.listdir("dist")
        for file in files:
            print(f"  - {file}")
    else:
        print("  No distribution files found.")

def check_requirements():
    """Check that all required files are in place."""
    required_files = ["pyproject.toml", "README.md", "LICENSE"]
    missing = [f for f in required_files if not os.path.exists(f)]
    
    if missing:
        print(f"Error: Missing required files: {', '.join(missing)}")
        sys.exit(1)
    
    # Make sure __version__ is defined in __init__.py
    init_file = "ailf/__init__.py"
    if os.path.exists(init_file):
        with open(init_file, "r") as f:
            content = f.read()
            if "__version__" not in content:
                print(f"Warning: __version__ not found in {init_file}")
    else:
        print(f"Warning: {init_file} not found")
    
    print("All required files present.")

def main():
    """Main function to run the build process."""
    check_requirements()
    clean_dist()
    build_package()
    list_dist()
    print("\nTo upload to PyPI, run: python -m twine upload dist/*")
    print("To upload to Test PyPI, run: python -m twine upload --repository testpypi dist/*")
    print("\nTo test installation: ./test_installation.py")
    
if __name__ == "__main__":
    main()
