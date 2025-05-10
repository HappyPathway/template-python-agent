#!/bin/bash
# Test the AILF Redis implementation

echo "====================================="
echo " AILF Redis Implementation Test"
echo "====================================="

# Check if Redis is available
redis_available=false

if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis server detected and running"
        redis_available=true
    else
        echo "⚠️ Redis CLI found but server not running"
    fi
else
    echo "⚠️ Redis CLI not found"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install package in development mode if not already installed
if ! pip show ailf &> /dev/null; then
    echo "Installing AILF package in development mode..."
    pip install -e .
fi

echo ""
echo "Running Redis implementation tests..."
echo ""

if [ "$redis_available" = true ]; then
    echo "Using real Redis server"
else
    echo "No Redis server detected - mock implementation will be used"
    # Set environment variable to use mock implementation
    export USE_MOCK_REDIS=true
fi

# Run the tests
python tests/test_ailf_redis.py

echo ""
echo "Test complete!"
