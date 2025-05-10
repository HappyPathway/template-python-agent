# Logging Module

This module provides a standardized logging configuration to ensure consistent logging behavior across your application.

## Overview

This module implements a consistent logging setup with the following features:

- **Standardized Formatting**: All logs follow a consistent format
- **Easy Setup**: Single function call to configure logging
- **Flexible Configuration**: Supports custom log levels and handlers
- **Avoid Duplicates**: Prevents duplicate handlers
- **Default Settings**: Sensible defaults for quick setup
- **File and Console Output**: Support for multiple output handlers
- **Log Rotation**: Automatic log file rotation
- **Context-aware Logging**: Add contextual information to logs

## Quick Start

```python
from ailf.logging import setup_logging

# Create a logger for your module
logger = setup_logging('my_module')

# Use the logger
logger.info('Application started')
logger.debug('Debug information')
logger.warning('Warning message')
```

## Configuration

By default, logs are formatted as:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

This includes:
- Timestamp
- Module name
- Log level
- Message content

The default configuration includes:
- Log Level: INFO
- Output: Console and rotating file handler
- File Location: `logs/app.log`

## Best Practices

1. Create one logger per module:
   ```python
   logger = setup_logging(__name__)
   ```

2. Use appropriate log levels:
   ```python
   logger.debug('Detailed information for debugging')
   logger.info('General information about program execution')
   logger.warning('Warning messages for potentially harmful situations')
   logger.error('Error messages for serious problems')
   logger.critical('Critical messages for fatal errors')
   ```

3. Include relevant context in log messages:
   ```python
   logger.error(f'Failed to process item {item_id}: {str(e)}')
   ```

4. Add structured data when applicable:
   ```python
   logger.info('User activity recorded', extra={'user_id': user.id, 'action': 'login'})
   ```

## API Reference

For detailed API documentation, see the {doc}`/api/logging` page.
