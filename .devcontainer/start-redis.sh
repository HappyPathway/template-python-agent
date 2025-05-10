#!/bin/bash
# Start Redis server if it's not already running - with robust error handling

set -e
set -o pipefail

echo "Starting Redis setup..."

# Create Redis configuration for development if it doesn't exist
REDIS_CONF="/tmp/redis-dev.conf"
if [ ! -f "$REDIS_CONF" ]; then
    echo "Creating Redis development configuration..."
    cat > "$REDIS_CONF" <<EOL
# Redis development configuration
port 6379
daemonize yes
loglevel notice
logfile /tmp/redis-dev.log
databases 16
save 900 1
save 300 10
save 60 10000
rdbcompression yes
dbfilename dump.rdb
dir /tmp
appendonly no
maxmemory 128mb
maxmemory-policy volatile-lru
EOL
    echo "✓ Redis configuration created"
fi

# Multiple methods to check if Redis is running
is_redis_running() {
    # Try pgrep first
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -x "redis-server" >/dev/null 2>&1 && return 0
    fi
    
    # Try systemctl if available
    if command -v systemctl >/dev/null 2>&1; then
        systemctl is-active --quiet redis-server 2>/dev/null && return 0
    fi
    
    # Try service if available
    if command -v service >/dev/null 2>&1; then
        service redis-server status >/dev/null 2>&1 && return 0
    fi
    
    # Try direct redis-cli ping
    if command -v redis-cli >/dev/null 2>&1; then
        redis-cli ping >/dev/null 2>&1 | grep -q "PONG" && return 0
    fi
    
    # Not running
    return 1
}

# Check if Redis is already running
if is_redis_running; then
    echo "Redis server is already running"
else
    echo "Starting Redis server with development configuration..."
    
    # Try multiple methods to start Redis
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q redis; then
        echo "Starting Redis with systemctl..."
        systemctl start redis-server || {
            echo "Failed to start with systemctl, trying direct method..."
            redis-server "$REDIS_CONF"
        }
    elif command -v service >/dev/null 2>&1 && service --status-all 2>&1 | grep -q redis; then
        echo "Starting Redis with service..."
        service redis-server start || {
            echo "Failed to start with service, trying direct method..."
            redis-server "$REDIS_CONF"
        }
    else
        echo "Starting Redis directly..."
        redis-server "$REDIS_CONF"
    fi
        # Wait for Redis to start up
    sleep 2
    
    # Verify Redis is running
    if is_redis_running; then
        echo "✓ Redis server started successfully"
    else
        echo "× Failed to start Redis server"
        # Continue with warning instead of failing
        echo "WARNING: Redis may not be available. Some functionality may not work."
    fi
fi

# Test Redis connection with retry
MAX_RETRY=3
RETRY_COUNT=0
REDIS_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRY ] && [ "$REDIS_OK" = "false" ]; do
    if redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo "✓ Redis connection successful"
        REDIS_OK=true
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRY ]; then
            echo "Retrying Redis connection ($RETRY_COUNT/$MAX_RETRY)..."
            sleep 2
        else
            echo "× Redis connection failed after $MAX_RETRY attempts"
            echo "WARNING: Redis may not be available. Some functionality may not work."
        fi
    fi
done

if [ "$REDIS_OK" = "true" ]; then
    echo "Redis is ready to use"
else
    # Create a marker file to indicate tests should skip Redis
    echo "Creating marker file to skip Redis-dependent tests"
    touch /tmp/SKIP_REDIS_TESTS
fi
