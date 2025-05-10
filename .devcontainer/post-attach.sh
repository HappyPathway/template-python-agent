#!/bin/bash
# Post-attach script for DevContainer

set -e
set -o pipefail

echo "==== Starting post-attach setup ===="

# Start SSH agent if SSH keys are available
echo "==== Setting up SSH agent (if keys available) ===="
if [ -d "$HOME/.ssh" ] && ls "$HOME/.ssh"/id_* 1> /dev/null 2>&1; then
    eval $(ssh-agent)
    find "$HOME/.ssh" -type f -name "id_*" ! -name "*.pub" -exec ssh-add {} \; 2>/dev/null || true
    echo "SSH agent started"
else
    echo "No SSH keys found, skipping SSH agent setup"
fi

# Start Redis safely using improved script
echo "==== Setting up Redis ===="
if [ -f ".devcontainer/start-redis.sh" ]; then
    sudo -E bash .devcontainer/start-redis.sh || echo "WARNING: Redis setup failed. Some functionality may not work."
else
    echo "No Redis start script found"
fi

echo "==== Post-attach setup completed ===="
