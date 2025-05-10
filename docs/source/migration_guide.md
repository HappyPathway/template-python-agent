# Migration Guide for Developers

This guide provides step-by-step instructions for developers involved in the repository reorganization project.

## Prerequisites

Before starting the migration, ensure you have:

1. A local development environment set up
2. All tests passing on your local machine
3. Git configured correctly
4. Necessary permissions for the repository

## Getting Started

Clone the repository if you haven't already:

```bash
git clone https://github.com/your-org/template-python-dev.git
cd template-python-dev
```

Make sure you have the latest changes:

```bash
git checkout main
git pull
```

## Phase 1: Schema Reorganization

### Step 1: Create Feature Branch

```bash
git checkout -b phase-1-schema-reorganization
```

### Step 2: Create Directory Structure

```bash
mkdir -p schemas/api
mkdir -p schemas/messaging
touch schemas/__init__.py
touch schemas/api/__init__.py
touch schemas/messaging/__init__.py
touch schemas/database.py
```

### Step 3: Move Schema Files

```bash
# Move AI schemas
cp utils/schemas/ai.py schemas/ai.py

# Move messaging schemas
cp utils/schemas/zmq.py schemas/messaging/zmq.py
cp utils/schemas/zmq_devices.py schemas/messaging/devices.py

# Move storage schemas
cp utils/schemas/storage.py schemas/storage.py

# Move test schemas
cp utils/schemas/test.py schemas/test.py
```

### Step 4: Update Imports

Use the following approach to update imports in all files:

1. First, create backward compatibility imports in old locations:

```python
# In utils/schemas/ai.py
import warnings
warnings.warn(
    "This module has moved to schemas.ai. Please update your imports.",
    DeprecationWarning,
    stacklevel=2
)
from schemas.ai import *  # Re-export everything
```

2. Then, update imports in the new location files:

```python
# In schemas/ai.py
# Updated imports to reference correct paths
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
```

3. Search for all files that import from old location and update them:

```bash
grep -r "from ailf.schemas.ai import" --include="*.py" .
```

### Step 5: Update __init__.py Files

Create appropriate exports in __init__.py files:

```python
# schemas/__init__.py
"""Schemas package for all data models.

This package contains all Pydantic models used throughout the application.
"""

# Import core models for easy access
from .ai import AIResponse, UsageLimits
from .storage import StorageConfig
from .database import DatabaseConfig

# Import sub-packages
from . import api
from . import messaging
```

### Step 6: Run Tests

```bash
make test
```

Fix any failing tests before proceeding.

### Step 7: Commit Changes

```bash
git add .
git commit -m "Phase 1: Schema reorganization"
git push origin phase-1-schema-reorganization
```

## Phase 2: Test Reorganization

Follow similar steps for test reorganization (see implementation_plan.md for detailed steps).

## Phase 3: Utils Reorganization

Follow similar steps for utils reorganization (see implementation_plan.md for detailed steps).

## Phase 4: Documentation Standardization

Follow similar steps for documentation standardization (see implementation_plan.md for detailed steps).

## Phase 5: Development Environment Improvement

Follow similar steps for development environment improvement (see implementation_plan.md for detailed steps).

## Troubleshooting

### Import Errors

If you encounter import errors:

1. Check the import path is correct
2. Make sure `__init__.py` files are in place
3. Verify that the module is exporting the required symbols

### Missing Files

If you get "file not found" errors:

1. Check if the file has been moved
2. Make sure the path is correct
3. Check if the file is included in the git repository

### Test Failures

If tests are failing:

1. Run tests with verbose output: `pytest -vv`
2. Check import paths in test files
3. Verify that all test fixtures are updated

### Documentation Build Failures

If documentation fails to build:

1. Check Sphinx configuration
2. Verify that all referenced files exist
3. Fix any docstring format issues

## Conclusion

By following this guide, you can contribute to the successful reorganization of the repository. Remember to:

1. Make changes in small, manageable increments
2. Run tests after each change
3. Document what you've done
4. Ask for help if you encounter difficulties

The end result will be a more maintainable, better organized codebase that is easier to develop with and extend.
