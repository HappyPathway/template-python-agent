#!/usr/bin/env python3
# Development environment setup script for Redis, Celery, and other dependencies

import os
import subprocess
import sys
import shutil
from pathlib import Path

MIN_PYTHON_VERSION = (3, 12)
VENV_DIR = "venv"
BASE_DIR = Path(__file__).resolve().parent.parent # Project root

def run_command(command, check=True, capture_output=False, text=True, shell=False):
    """Helper function to run a shell command."""
    print(f"Running: {' '.join(command) if isinstance(command, list) else command}")
    try:
        result = subprocess.run(command, check=check, capture_output=capture_output, text=text, shell=shell)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if capture_output:
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}")
        sys.exit(1)

def check_python_version():
    """Checks if the current Python version meets the minimum requirement."""
    print("Checking Python version...")
    if sys.version_info < MIN_PYTHON_VERSION:
        print(f"Error: This project requires Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or higher.")
        print(f"Current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        sys.exit(1)
    print(f"Python version {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} is compatible.")

def install_redis():
    """Attempts to install Redis if not found."""
    print("Installing Redis...")
    if shutil.which("apt-get"):
        print("Attempting Redis installation for Debian/Ubuntu...")
        run_command(["sudo", "apt-get", "update"])
        run_command(["sudo", "apt-get", "install", "-y", "redis-server"])
    elif shutil.which("yum"):
        print("Attempting Redis installation for RHEL/CentOS/Fedora...")
        run_command(["sudo", "yum", "install", "-y", "redis"])
    elif shutil.which("brew"):
        print("Attempting Redis installation for macOS...")
        run_command(["brew", "install", "redis"])
    else:
        print("Unsupported OS for automatic Redis installation. Please install Redis manually.")
        sys.exit(1)

def check_and_start_redis():
    """Checks if Redis is installed and running, starts it if necessary."""
    print("Checking Redis status...")
    if not shutil.which("redis-server"):
        install_redis()

    # Check if Redis is running by trying to ping it
    redis_cli_path = shutil.which("redis-cli")
    if redis_cli_path:
        try:
            result = run_command([redis_cli_path, "ping"], capture_output=True, check=False)
            if result.returncode == 0 and "PONG" in result.stdout:
                print("Redis server is running.")
                return
        except Exception:
            pass # Will attempt to start if ping fails or redis-cli not found initially

    print("Attempting to start Redis server...")
    try:
        # Attempt to start Redis. This might require sudo or specific service commands
        # depending on the OS and how Redis was installed.
        # A common way is to just call redis-server if it's in PATH.
        run_command(["redis-server", "--daemonize", "yes"], check=False)
        # Verify again
        import time
        time.sleep(2) # Give it a moment to start
        result = run_command([redis_cli_path, "ping"], capture_output=True, check=True)
        if "PONG" in result.stdout:
            print("Redis server started successfully.")
        else:
            print("Failed to start Redis server or confirm it's running. Please check your Redis installation.")
            # sys.exit(1) # Decided not to exit, to allow setup to continue if Redis is managed externally
    except Exception as e:
        print(f"Could not start Redis: {e}. Please ensure Redis is installed and running.")
        # sys.exit(1)


def setup_virtual_environment():
    """Creates a Python virtual environment if it doesn't exist."""
    venv_path = BASE_DIR / VENV_DIR
    if not venv_path.is_dir():
        print("Creating Python virtual environment...")
        run_command([sys.executable, "-m", "venv", str(venv_path)])
    else:
        print("Virtual environment already exists.")
    
    # Define paths to python and pip in venv
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    return str(python_exe), str(pip_exe)

def install_dependencies(pip_exe):
    """Installs Python dependencies from requirements files."""
    print("Installing Python dependencies...")
    requirements_txt = BASE_DIR / "requirements.txt"
    dev_requirements_txt = BASE_DIR / "setup" / "requirements" / "dev.txt" # Adjusted path

    if requirements_txt.exists():
        run_command([pip_exe, "install", "-r", str(requirements_txt)])
    else:
        print(f"Warning: {requirements_txt} not found.")

    if dev_requirements_txt.exists():
        print("Installing development tools...")
        run_command([pip_exe, "install", "-r", str(dev_requirements_txt)])
    else:
        print(f"Warning: {dev_requirements_txt} not found. Looked in setup/requirements/dev.txt")


def create_directories():
    """Creates necessary directories."""
    print("Creating necessary directories...")
    os.makedirs(BASE_DIR / "logs", exist_ok=True)
    os.makedirs(BASE_DIR / "data" / "local_storage", exist_ok=True)

def setup_env_file():
    """Copies .env.example to .env if .env doesn't exist."""
    print("Setting up environment variables...")
    env_file = BASE_DIR / ".env"
    env_example_file = BASE_DIR / ".env.example"

    if not env_file.exists() and env_example_file.exists():
        shutil.copy(str(env_example_file), str(env_file))
        print("Created .env file from example. Please update with your settings.")
    elif env_file.exists():
        print(".env file already exists.")
    else:
        print("Warning: .env.example not found. Cannot create .env file.")

def test_setup(python_exe):
    """Runs simple tests to verify the setup."""
    print("Testing setup...")
    
    # Test Redis connection
    print("Testing Redis connection...")
    try:
        # Ensure redis package is installed before trying to import
        run_command([python_exe, "-m", "pip", "show", "redis"], capture_output=True) # Check if installed
        run_command([python_exe, "-c", "import redis; r = redis.Redis(decode_responses=True); assert r.ping() == True; print('Redis is working correctly!')"])
    except Exception as e:
        print(f"Redis connection test failed: {e}. Ensure Redis is running and accessible.")
        print("Attempting to install redis package if missing...")
        pip_exe = Path(python_exe).parent / "pip"
        run_command([str(pip_exe), "install", "redis"])
        print("Retrying Redis connection test...")
        try:
            run_command([python_exe, "-c", "import redis; r = redis.Redis(decode_responses=True); assert r.ping() == True; print('Redis is working correctly!')"])
        except Exception as e_retry:
            print(f"Redis connection test failed again: {e_retry}")


    # Test Celery (basic import, assumes celery is in requirements)
    # Note: Celery worker imports might fail if full app setup isn't complete
    # or if other dependencies (like message broker) aren't running.
    # This is a very basic check.
    print("Testing Celery configuration (basic import)...")
    celery_test_code = """
try:
    # Adjust the import path according to your project structure
    # This path might need to be updated after import refactoring
   