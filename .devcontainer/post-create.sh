#!/bin/bash
# Post-create setup script for DevContainer

set -e
set -o pipefail

echo "==== Starting post-create setup ===="

# Setup workspace directory
echo "==== Setting up workspace directory ===="
mkdir -p /workspace
chown -R vscode:vscode /workspace

# Install requirements with error handling
echo "==== Installing Python requirements ===="
if [ -f "requirements.txt" ]; then
    echo "Installing from requirements.txt"
    pip install -r requirements.txt || echo "WARNING: Some requirements failed to install"
else
    echo "Installing base requirements"
    pip install -r requirements/base.txt || echo "WARNING: Some requirements failed to install"
fi

# Set up SSH directory with proper permissions (if it exists)
echo "==== Setting up SSH (if available) ===="
if [ -d "$HOME/.ssh" ]; then
    echo "Setting SSH directory permissions"
    chmod 700 "$HOME/.ssh" || true
    find "$HOME/.ssh" -type f -name "id_*" ! -name "*.pub" -exec chmod 600 {} \; || true
    find "$HOME/.ssh" -type f -name "*.pub" -exec chmod 644 {} \; || true
    find "$HOME/.ssh" -type f -name "config" -exec chmod 600 {} \; || true
else
    echo "No SSH directory found"
fi

# Create a default .env file if it doesn't exist
if [ ! -f "/workspace/.env" ]; then
    echo "==== Creating default .env file ===="
    cat > /workspace/.env <<EOL
# Default environment variables
ENVIRONMENT=development
# Add more environment variables as needed
EOL
    echo "Created default .env file"
fi

# Install additional tools
echo "==== Installing additional tools ===="
if [ -f ".devcontainer/install-tools.sh" ]; then
    sudo -E bash .devcontainer/install-tools.sh || echo "WARNING: Some tools failed to install"
else
    echo "No install-tools.sh script found"
fi

echo "==== Post-create setup completed ===="
