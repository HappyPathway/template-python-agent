"""Interaction Logger for AILF agents."""

import abc
import logging
from typing import Any, Dict, Optional

from ailf.schemas.feedback import LoggedInteraction

# Get a logger for this module
logger = logging.getLogger(__name__)

class BaseLogStorage(abc.ABC):
    """Abstract base class for interaction log storage backends."""

    @abc.abstractmethod
    async def store_interaction(self, interaction: LoggedInteraction) -> None:
        """
        Store a single LoggedInteraction instance.

        :param interaction: The LoggedInteraction to store.
        :type interaction: LoggedInteraction
        :raises NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

    async def setup(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Optional setup method for the storage backend."""
        pass

    async def teardown(self) -> None:
        """Optional teardown method for the storage backend."""
        pass

class ConsoleLogStorage(BaseLogStorage):
    """A simple interaction log storage backend that prints to the console."""

    async def store_interaction(self, interaction: LoggedInteraction) -> None:
        """
        Prints the LoggedInteraction to the console.

        :param interaction: The LoggedInteraction to print.
        :type interaction: LoggedInteraction
        """
        logger.info(f"LoggedInteraction: {interaction.interaction_id}")
        logger.debug(interaction.model_dump_json(indent=2))

class InteractionLogger:
    """
    Handles the logging of agent interactions using a configurable storage backend.
    """

    def __init__(self, storage_backend: Optional[BaseLogStorage] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the InteractionLogger.

        :param storage_backend: An instance of a class derived from BaseLogStorage.
                                If None, ConsoleLogStorage will be used.
        :type storage_backend: Optional[BaseLogStorage]
        :param config: Configuration dictionary for the storage backend.
        :type config: Optional[Dict[str, Any]]
        """
        self.storage_backend = storage_backend or ConsoleLogStorage()
        self._config = config or {}
        self._is_setup = False

    async def setup(self) -> None:
        """
        Set up the interaction logger and its storage backend.
        This should be called before logging any interactions.
        """
        if not self._is_setup:
            await self.storage_backend.setup(self._config)
            self._is_setup = True
            logger.info(f"InteractionLogger setup with backend: {self.storage_backend.__class__.__name__}")

    async def teardown(self) -> None:
        """
        Clean up resources used by the interaction logger and its storage backend.
        """
        if self._is_setup:
            await self.storage_backend.teardown()
            self._is_setup = False
            logger.info(f"InteractionLogger teardown for backend: {self.storage_backend.__class__.__name__}")

    async def log_interaction(self, **kwargs: Any) -> LoggedInteraction:
        """
        Logs an interaction by creating a LoggedInteraction instance and storing it.

        All keyword arguments are passed to the LoggedInteraction model constructor.

        :param kwargs: Fields for the LoggedInteraction model.
        :type kwargs: Any
        :return: The created LoggedInteraction instance.
        :rtype: LoggedInteraction
        :raises RuntimeError: If the logger is not setup.
        """
        if not self._is_setup:
            # Automatically setup if not already done, for convenience in simple cases.
            # For more complex setups, explicit setup is recommended.
            logger.warning("InteractionLogger.log_interaction() called before explicit setup. Performing automatic setup.")
            await self.setup()
        
        interaction = LoggedInteraction(**kwargs)
        await self.storage_backend.store_interaction(interaction)
        logger.debug(f"Successfully logged interaction: {interaction.interaction_id}")
        return interaction

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()
