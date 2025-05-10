#!/bin/bash
# Test script to verify the consolidation was successful

echo "Running tests to verify the consolidation..."

# Run basic imports test
python -c "from ailf import AIEngine; print('AIEngine import successful')"
python -c "from ailf.core import storage, logging; print('Core modules import successful')"
python -c "from ailf.messaging import redis, zmq; print('Messaging modules import successful')"
python -c "from ailf.schemas import ai, mcp; print('Schema modules import successful')"

# Run the example file
echo -e "\nTesting an example file (without executing it)..."
python -c "import examples.custom_ai_engine; print('Example imports successfully')"

# Run tests
echo -e "\nRunning unit tests..."
pytest tests/unit -v

echo -e "\nConsolidation testing complete."
