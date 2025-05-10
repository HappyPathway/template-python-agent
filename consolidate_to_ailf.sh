#!/bin/bash
# Migration script to consolidate utils into ailf

# Step 1: Create missing directories in ailf
echo "Creating missing directories in ailf..."
mkdir -p /workspaces/template-python-dev/ailf/workers
mkdir -p /workspaces/template-python-dev/ailf/schemas
mkdir -p /workspaces/template-python-dev/ailf/messaging

# Handle special case for multi-line imports in ailf modules
echo "Handling multi-line imports in ailf modules..."
find /workspaces/template-python-dev/ailf -type f -name "*.py" | xargs sed -i 's/from utils\.\([a-zA-Z_]*\) import/from ailf.\1 import/g'

# Step 2: Copy missing files from utils to ailf
echo "Copying missing files from utils to ailf..."

# Copy async_tasks.py
cp /workspaces/template-python-dev/utils/async_tasks.py /workspaces/template-python-dev/ailf/

# Copy workers modules
cp /workspaces/template-python-dev/utils/workers/tasks.py /workspaces/template-python-dev/ailf/workers/
cp /workspaces/template-python-dev/utils/workers/celery_app.py /workspaces/template-python-dev/ailf/workers/

# Copy messaging modules
cp /workspaces/template-python-dev/utils/messaging/async_redis.py /workspaces/template-python-dev/ailf/messaging/
cp /workspaces/template-python-dev/utils/messaging/mock_redis.py /workspaces/template-python-dev/ailf/messaging/

# Copy schema modules
cp /workspaces/template-python-dev/utils/schemas/documentation.py /workspaces/template-python-dev/ailf/schemas/
cp /workspaces/template-python-dev/utils/schemas/test.py /workspaces/template-python-dev/ailf/schemas/
cp /workspaces/template-python-dev/utils/schemas/zmq.py /workspaces/template-python-dev/ailf/schemas/
cp /workspaces/template-python-dev/utils/schemas/storage.py /workspaces/template-python-dev/ailf/schemas/

# Copy other utilities
cp /workspaces/template-python-dev/utils/gcs_config_stash.py /workspaces/template-python-dev/ailf/
cp /workspaces/template-python-dev/utils/github_client.py /workspaces/template-python-dev/ailf/
cp /workspaces/template-python-dev/utils/setup_storage.py /workspaces/template-python-dev/ailf/

# Step 3: Update import statements in the copied files
echo "Updating import statements in copied files..."
find /workspaces/template-python-dev/ailf -type f -name "*.py" -exec sed -i 's/from utils\./from ailf\./g' {} \;
find /workspaces/template-python-dev/ailf -type f -name "*.py" -exec sed -i 's/import utils\./import ailf\./g' {} \;

# Step 4: Update references in examples and tests
echo "Updating import statements in examples and tests..."
find /workspaces/template-python-dev/examples -type f -name "*.py" -exec sed -i 's/from utils\./from ailf\./g' {} \;
find /workspaces/template-python-dev/examples -type f -name "*.py" -exec sed -i 's/import utils\./import ailf\./g' {} \;
find /workspaces/template-python-dev/tests -type f -name "*.py" -exec sed -i 's/from utils\./from ailf\./g' {} \;
find /workspaces/template-python-dev/tests -type f -name "*.py" -exec sed -i 's/import utils\./import ailf\./g' {} \;

# Step 5: Update documentation
echo "Updating import statements in documentation..."
find /workspaces/template-python-dev/docs -type f -name "*.md" -exec sed -i 's/from utils\./from ailf\./g' {} \;
find /workspaces/template-python-dev/docs -type f -name "*.md" -exec sed -i 's/import utils\./import ailf\./g' {} \;
find /workspaces/template-python-dev/docs -type f -name "*.md" -exec sed -i 's/>>> from utils\./>>> from ailf\./g' {} \;

echo "Migration complete. Please review the changes and test thoroughly."
echo ""
echo "Note: If you encounter circular imports, you may need to fix them manually:"
echo "1. Check for instances of 'from ailf.X import (...)' where X is the current module"
echo "2. Replace with relative imports if needed, e.g., 'from . import X' in __init__.py files"
echo "3. Update any recursive imports in ailf/web_scraper.py, ailf/base_mcp.py, etc."
