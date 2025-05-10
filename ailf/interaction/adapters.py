"""Base classes for input and output adapters in the AILF interaction module."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ailf.schemas.interaction import AnyInteractionMessage

# Type variable for the raw input data format
InputFormat = TypeVar("InputFormat")
# Type variable for the raw output data format
OutputFormat = TypeVar("OutputFormat")

class BaseInputAdapter(ABC, Generic[InputFormat]):
    """
    Abstract base class for input adapters.
    Input adapters are responsible for converting raw input data from various sources
    into a standardized `AnyInteractionMessage` format that the agent can understand.
    """

    @abstractmethod
    async def parse(self, raw_input: InputFormat) -> AnyInteractionMessage:
        """
        Parse the raw input data and convert it into a standardized message.

        :param raw_input: The raw input data in its original format.
        :type raw_input: InputFormat
        :return: A standardized interaction message.
        :rtype: AnyInteractionMessage
        :raises NotImplementedError: If the method is not implemented by a subclass.
        :raises ValueError: If the input data is malformed or cannot be parsed.
        """
        raise NotImplementedError("Subclasses must implement the parse method.")

class BaseOutputAdapter(ABC, Generic[OutputFormat]):
    """
    Abstract base class for output adapters.
    Output adapters are responsible for converting a standardized `AnyInteractionMessage`
    from the agent into a raw output format suitable for a specific channel or system.
    """

    @abstractmethod
    async def format(self, message: AnyInteractionMessage) -> OutputFormat:
        """
        Format the standardized message into the target raw output format.

        :param message: The standardized interaction message from the agent.
        :type message: AnyInteractionMessage
        :return: The raw output data in the target format.
        :rtype: OutputFormat
        :raises NotImplementedError: If the method is not implemented by a subclass.
        :raises ValueError: If the message cannot be formatted for the target output.
        """
        raise NotImplementedError("Subclasses must implement the format method.")