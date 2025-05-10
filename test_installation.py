#!/usr/bin/env python3
"""Test script to verify the AILF package installation.

This script:
1. Creates and activates a virtual environment
2. Installs the package with all extras from the local dist directory
3. Runs basic import tests to ensure the package works correctly
"""
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run command and return output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, 
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)
        
    return result.stdout.strip()

def main():
    """Main function."""
    # Ensure we have a dist directory with built packages
    dist_dir = Path("dist")
    if not dist_dir.exists() or not list(dist_dir.glob("*.whl")):
        print("No wheel package found in the dist directory. Building package first...")
        run_command([sys.executable, "build_dist.py"])
    
    # Create a temporary directory for the venv
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_dir = Path(temp_dir) / "venv"
        print(f"Creating virtual environment at {venv_dir}...")
        venv.create(venv_dir, with_pip=True)
        
        # Determine path to pip in the venv
        if sys.platform == "win32":
            pip_path = venv_dir / "Scripts" / "pip"
        else:
            pip_path = venv_dir / "bin" / "pip"
            
        # Install the package from the wheel
        wheel_file = list(dist_dir.glob("*.whl"))[0]
        print(f"Installing {wheel_file.name}...")
        run_command([str(pip_path), "install", f"{wheel_file}[all]"])
        
        # Create a test script
        test_script = """
import sys
import importlib

modules_to_test = [
    "ailf",
    "ailf.core.logging", 
    "ailf.core.storage",
    "ailf.ai_engine", 
    "ailf.messaging.zmq", 
    "ailf.messaging.redis",
    "ailf.schemas.mcp"
]

def test_imports():
    """Test importing key modules."""
    for module in modules_to_test:
        print(f"Testing import of {module}...", end=" ")
        try:
            importlib.import_module(module)
            print("OK")
        except ImportError as e:
            print(f"FAILED: {str(e)}")
            return False
    return True

if not test_imports():
    print("Import tests failed!")
    sys.exit(1)

# Test a simple feature
from ailf import setup_logging
logger = setup_logging("test")
logger.info("Package import test successful!")

print("\\nAll tests passed! The package was installed successfully.")
"""
        
        test_script_path = Path(temp_dir) / "test_installation.py"
        with open(test_script_path, "w") as f:
            f.write(test_script)
            
        # Run the test script using the venv's Python
        if sys.platform == "win32":
            python_path = venv_dir / "Scripts" / "python"
        else:
            python_path = venv_dir / "bin" / "python"
            
        print("\nTesting package imports...")
        run_command([str(python_path), str(test_script_path)])
        
    print("\n✅ Package installation test successful! The package was built, installed and imported correctly.")

if __name__ == "__main__":
    main()
