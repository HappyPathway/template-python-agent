# Requirements Management

This directory contains segmented requirements files for reference and development purposes. 

> **Note:** The main project uses a consolidated approach with a single `requirements.txt` file in the root directory that contains all dependencies. These individual files are kept for reference and specialized use cases.

## Consolidated Approach (Recommended)

For most use cases, install all dependencies from the root directory:

```bash
pip install -r requirements.txt
```

## Individual Files Reference

These files document the dependencies for specific features and environments:

- `base.txt` - Core dependencies required for minimal functionality
- `ai.txt` - AI model integrations (OpenAI, Anthropic, Google)
- `mcp.txt` - Model Context Protocol server dependencies
- `cloud.txt` - Cloud service integrations (GCP)
- `zmq.txt` - ZeroMQ messaging dependencies
- `redis.txt` - Redis messaging and caching dependencies
- `dev.txt` - Development tools and testing libraries
- `prod.txt` - Production-specific dependencies

## Using setup.py

Alternatively, you can use the setup.py extras from the root directory:

```bash
# Basic installation (from the root directory)
pip install -e .

# With specific features
pip install -e ".[ai]"
pip install -e ".[mcp]"
pip install -e ".[cloud]"
pip install -e ".[zmq]"

# Combined features
pip install -e ".[ai,mcp]"  # For building an AI agent with MCP

# Development
pip install -e ".[dev]"

# Full installation
pip install -e ".[all]"
```

> **Important:** Always run these commands from the root directory of the project, not from the requirements directory.
