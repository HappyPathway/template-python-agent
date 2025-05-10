#!/usr/bin/env python3
"""
Interactive build workflow script for the AILF package.

This script guides you through the process of:
1. Cleaning the project
2. Running tests
3. Building the package
4. Testing the installation
5. Publishing to PyPI

Use this script for a complete workflow instead of running individual scripts.
"""
import os
import subprocess
import sys
from pathlib import Path

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def run_command(cmd, cwd=None, check=True):
    """Run a command and print output."""
    print(f"\n> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=check)
    return result.returncode == 0

def prompt_yes_no(question, default="yes"):
    """Ask a yes/no question via input() and return the answer."""
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError(f"Invalid default answer: '{default}'")
    
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

def clean():
    """Clean the project."""
    print_header("CLEANING PROJECT")
    dirs_to_remove = [
        "dist", 
        "build", 
        "*.egg-info",
        "**/__pycache__", 
        ".pytest_cache"
    ]
    
    for pattern in dirs_to_remove:
        files = list(Path(".").glob(pattern))
        if files:
            for file in files:
                if file.is_dir():
                    print(f"Removing directory: {file}")
                    try:
                        import shutil
                        shutil.rmtree(file)
                    except Exception as e:
                        print(f"Error removing {file}: {e}")
                else:
                    print(f"Removing file: {file}")
                    file.unlink()

def run_tests():
    """Run the test suite."""
    print_header("RUNNING TESTS")
    return run_command([sys.executable, "-m", "pytest", "-v"])

def build_package():
    """Build the package."""
    print_header("BUILDING PACKAGE")
    return run_command([sys.executable, "build_dist.py"])
    
def test_installation():
    """Test package installation."""
    print_header("TESTING INSTALLATION")
    return run_command([sys.executable, "test_installation.py"])
    
def publish_package():
    """Publish the package to PyPI."""
    print_header("PUBLISHING PACKAGE")
    
    if prompt_yes_no("Publish to Test PyPI first?"):
        run_command([sys.executable, "-m", "pip", "install", "--upgrade", "twine"])
        run_command([
            sys.executable, "-m", "twine", "upload", 
            "--repository-url", "https://test.pypi.org/legacy/", 
            "dist/*"
        ], check=False)
        
        print("\nTest PyPI URL: https://test.pypi.org/project/ailf/")
        
        if prompt_yes_no("Test installation from Test PyPI?"):
            run_command([
                sys.executable, "-m", "pip", "install", 
                "--index-url", "https://test.pypi.org/simple/", 
                "--no-deps", "ailf"
            ], check=False)
    
    if prompt_yes_no("Publish to PyPI?"):
        run_command([
            sys.executable, "-m", "twine", "upload", "dist/*"
        ], check=False)
        
        print("\nPyPI URL: https://pypi.org/project/ailf/")

def main():
    """Main workflow function."""
    print_header("AILF PACKAGE BUILD WORKFLOW")
    
    workflow_steps = [
        ("Clean project", clean),
        ("Run tests", run_tests),
        ("Build package", build_package),
        ("Test installation", test_installation),
        ("Publish package", publish_package),
    ]
    
    for i, (step_name, step_func) in enumerate(workflow_steps, 1):
        print(f"\n{i}. {step_name}")
        
    while True:
        try:
            choice = int(input("\nSelect a step to run (1-5), or 0 to run all: "))
            if choice == 0:
                for _, step_func in workflow_steps:
                    if not step_func():
                        print("Workflow stopped due to error.")
                        break
                break
            elif 1 <= choice <= len(workflow_steps):
                workflow_steps[choice-1][1]()
            else:
                print(f"Please enter a number between 0 and {len(workflow_steps)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nWorkflow cancelled.")
            break
            
    print("\nWorkflow completed!")

if __name__ == "__main__":
    main()
