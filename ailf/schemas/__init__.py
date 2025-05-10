"""AILF Schemas Package.

This package consolidates all Pydantic models used across the AILF framework,
ensuring a single source of truth for data structures.
"""

# Import and re-export schemas from submodules
from .acp import *  # noqa: F403, F401 (ACP schemas)
from .cognition import *  # noqa: F403, F401 (Cognition schemas)
from .feedback import *  # noqa: F403, F401 (Feedback schemas)
from .interaction import * # noqa: F403, F401 (Interaction schemas)
from .memory import *  # noqa: F403, F401 (Memory schemas)
from .mcp import * # noqa: F403, F401 (MCP Schemas)
from .routing import * # noqa: F403, F401 (Routing schemas)
from .tooling import * # noqa: F403, F401 (Tooling schemas)
from .agent import *   # noqa: F403, F401 (Agent description schemas)

# It's good practice to define __all__ to specify what gets imported with a wildcard
# However, for a central schema package like this, often all defined schemas in submodules are desired.
# If specific control is needed, list them explicitly.
# For now, relying on the submodule __all__ definitions if they exist, or direct imports.