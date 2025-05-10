"""AILF Communication Package.

This package provides components for inter-agent communication, including
the Agent Communication Protocol (ACP) handling and integration with
various messaging backends.

Key Components:
    ACPHandler: Manages sending and receiving structured ACP messages.
"""

from .handler import ACPHandler

__all__ = [
    "ACPHandler",
]
