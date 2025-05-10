# Agent Capabilities Map

This document provides a high-level overview of the capabilities available in the template-python-dev repository, organized by functional area. Use this as a quick reference to locate specific functionality within the codebase.

## AI/LLM Integration

| Capability | Module | Description |
|------------|--------|-------------|
| Text Generation | `ailf.ai_engine` | Core text generation with multiple provider support (OpenAI, Anthropic, Google) |
| Structured Output | `ailf.schemas.ai` | Pydantic models for structured LLM outputs |
| Content Analysis | `ailf.ai_engine` | Content analysis with various analysis types |
| Classification | `ailf.ai_engine` | Classification of text into predefined categories |
| MCP Integration | `ailf.base_mcp` | Model Context Protocol server implementation |

## Messaging & Communication

| Capability | Module | Description |
|------------|--------|-------------|
| ZeroMQ Messaging | `ailf.zmq` | High-performance messaging using ZeroMQ |
| ZMQ Patterns | `ailf.zmq_devices` | Implementation of common ZMQ patterns (pub/sub, push/pull, etc.) |
| Redis PubSub | `ailf.messaging.redis` | Real-time messaging with Redis Pub/Sub |
| Redis Streams | `ailf.messaging.redis` | Persistent, ordered message processing with Redis Streams |
| Distributed Coordination | `ailf.messaging.redis` | Locks, rate limiting, and synchronization primitives |

## Task Processing

| Capability | Module | Description |
|------------|--------|-------------|
| Async Task Management | `ailf.async_tasks` | AsyncIO-based task management, tracking, and coordination |
| Distributed Tasks | `ailf.workers.celery_app` | Distributed task processing with Celery |
| Task State Management | `ailf.workers.tasks` | Task status tracking and error handling |
| Task Progress Updates | `ailf.async_tasks` | Real-time progress tracking for long-running tasks |
| Task Monitoring | `ailf.monitoring` | Performance monitoring and instrumentation |

## Storage & Data Management

| Capability | Module | Description |
|------------|--------|-------------|
| Local Storage | `ailf.storage` | Local file system storage operations |
| Google Cloud Storage | `ailf.storage` | Cloud storage with GCS integration |
| Database Operations | `ailf.database` | Database connection and session management |
| JSON Document Storage | `ailf.storage` | JSON document storage and retrieval |
| Schema Validation | `ailf.schemas.*` | Pydantic models for data validation |

## Authentication & Security

| Capability | Module | Description |
|------------|--------|-------------|
| Secret Management | `ailf.secrets` | Secure secrets management with Google Secret Manager |
| GitHub Authentication | `ailf.github_client` | GitHub API authentication |
| GCP Authentication | `ailf.gcs_config_stash` | Google Cloud authentication |
| Redis Security | `ailf.messaging.redis` | Secure Redis connection handling |

## Operational Support

| Capability | Module | Description |
|------------|--------|-------------|
| Logging | `ailf.logging` | Centralized, configurable logging |
| Monitoring | `ailf.monitoring` | Performance metrics and instrumentation |
| Error Handling | Various modules | Standardized error handling patterns |
| Web Scraping | `ailf.web_scraper` | Rate-limited, respectful web content retrieval |

## Integration Patterns

| Pattern | Example | Description |
|---------|---------|-------------|
| AsyncIO + Redis | `examples.async_redis_celery_example` | Combining AsyncIO with Redis messaging |
| AsyncIO + Celery | `examples.async_redis_celery_example` | Using AsyncIO to coordinate Celery tasks |
| MCP + AsyncIO | `examples.mcp_async_redis_example` | MCP server with AsyncIO task management |
| Multi-Protocol Agent | `examples.multi_protocol_agent` | Agent supporting multiple messaging protocols |
| Distributed Processing | `examples.integrated_agent_system` | Fully integrated system with multiple components |

## Extension Points

The following modules provide clear extension points through inheritance:

| Module | Extension Points | Purpose |
|--------|------------------|---------|
| `ailf.ai_engine` | `_setup_provider`, `_get_provider_settings` | Customize AI provider handling |
| `ailf.storage` | `_get_default_dirs`, `_ensure_dir_exists` | Customize storage structure |
| `ailf.zmq` | `_create_socket`, `_handle_recv` | Custom ZeroMQ behaviors |
| `ailf.base_mcp` | `_setup`, `_process_message` | MCP server customization |
| `ailf.async_tasks` | `_cleanup_completed` | Custom task cleanup logic |
