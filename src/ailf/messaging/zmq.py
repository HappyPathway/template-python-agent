"""ZeroMQ messaging utilities.

This module provides ZeroMQ-based messaging patterns for distributed systems.
"""

try:
    from utils.zmq import (
        ZMQBase,
        ZMQPublisher,
        ZMQSubscriber,
        ZMQClient,
        ZMQServer
    )
except ImportError:
    # Fallback implementations for when the package is installed standalone
    import zmq
    from typing import Any, Dict, List, Optional, Tuple, Union
    
    class ZMQBase:
        """Base class for ZMQ patterns."""
        
        def __init__(self, context: Optional[zmq.Context] = None):
            """Initialize with ZeroMQ context.
            
            Args:
                context: ZMQ context (creates new one if None)
            """
            self.context = context or zmq.Context.instance()
            self.socket = None
            self.socket_type = None
            self._connected = False
            
        def connect(self, address: str) -> None:
            """Connect to an endpoint.
            
            Args:
                address: ZMQ socket address to connect to
            """
            self._ensure_socket()
            self.socket.connect(address)
            self._connected = True
            
        def bind(self, address: str) -> None:
            """Bind to an endpoint.
            
            Args:
                address: ZMQ socket address to bind to
            """
            self._ensure_socket()
            self.socket.bind(address)
            self._connected = True
            
        def close(self) -> None:
            """Close the socket."""
            if self.socket:
                self.socket.close()
                self.socket = None
                self._connected = False
                
        def _ensure_socket(self) -> None:
            """Ensure socket is created."""
            if not self.socket and self.socket_type:
                self.socket = self.context.socket(self.socket_type)
                
        def __del__(self):
            """Clean up resources."""
            self.close()
    
    class ZMQPublisher(ZMQBase):
        """ZMQ Publisher pattern.
        
        Implements the publish-subscribe messaging pattern where
        a publisher sends messages to multiple subscribers.
        """
        
        def __init__(self, context: Optional[zmq.Context] = None):
            """Initialize publisher.
            
            Args:
                context: ZMQ context to use (creates new one if None)
            """
            super().__init__(context)
            self.socket_type = zmq.PUB
            self._ensure_socket()
            
        def publish(self, topic: str, message: Union[str, bytes, dict]) -> None:
            """Publish a message with the given topic.
            
            Args:
                topic: Message topic (used for filtering by subscribers)
                message: Message content (string, bytes, or dict)
            """
            if not self._connected:
                raise RuntimeError("Publisher not connected to an endpoint")
                
            # Prepare message based on its type
            if isinstance(message, dict):
                import json
                message_data = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                message_data = message.encode('utf-8')
            else:
                message_data = message
                
            # Send the message with topic prefix
            topic_bytes = topic.encode('utf-8') if isinstance(topic, str) else topic
            self.socket.send_multipart([topic_bytes, message_data])
    
    class ZMQSubscriber(ZMQBase):
        """ZMQ Subscriber pattern.
        
        Implements the subscribe part of the publish-subscribe messaging pattern,
        receiving messages published by publishers based on topic filters.
        """
        
        def __init__(self, context: Optional[zmq.Context] = None):
            """Initialize subscriber.
            
            Args:
                context: ZMQ context to use (creates new one if None)
            """
            super().__init__(context)
            self.socket_type = zmq.SUB
            self._ensure_socket()
            
        def subscribe(self, topic: str) -> None:
            """Subscribe to a topic.
            
            Args:
                topic: Topic to subscribe to
            """
            if not self.socket:
                raise RuntimeError("Socket not initialized")
                
            topic_bytes = topic.encode('utf-8') if isinstance(topic, str) else topic
            self.socket.setsockopt(zmq.SUBSCRIBE, topic_bytes)
            
        def unsubscribe(self, topic: str) -> None:
            """Unsubscribe from a topic.
            
            Args:
                topic: Topic to unsubscribe from
            """
            if not self.socket:
                raise RuntimeError("Socket not initialized")
                
            topic_bytes = topic.encode('utf-8') if isinstance(topic, str) else topic
            self.socket.setsockopt(zmq.UNSUBSCRIBE, topic_bytes)
            
        def receive(self, timeout: int = -1) -> Tuple[str, Union[str, bytes]]:
            """Receive a message.
            
            Args:
                timeout: Receive timeout in milliseconds (-1 for indefinite)
                
            Returns:
                Tuple[str, Union[str, bytes]]: Topic and message content
                
            Raises:
                zmq.Again: If no message is available within timeout
            """
            if not self._connected:
                raise RuntimeError("Subscriber not connected to an endpoint")
                
            if timeout >= 0:
                # Set timeout only if specified
                old_timeout = self.socket.RCVTIMEO
                self.socket.setsockopt(zmq.RCVTIMEO, timeout)
                
            try:
                # Receive topic and message as multipart message
                topic_bytes, message_bytes = self.socket.recv_multipart()
                topic = topic_bytes.decode('utf-8')
                
                # Try to decode as string, but fall back to bytes if not UTF-8
                try:
                    message = message_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    message = message_bytes
                    
                return topic, message
                
            finally:
                if timeout >= 0:
                    # Restore original timeout
                    self.socket.setsockopt(zmq.RCVTIMEO, old_timeout)
    
    class ZMQClient(ZMQBase):
        """ZMQ Client pattern.
        
        Implements the request part of the request-reply pattern.
        """
        
        def __init__(self, context: Optional[zmq.Context] = None):
            """Initialize client.
            
            Args:
                context: ZMQ context to use (creates new one if None)
            """
            super().__init__(context)
            self.socket_type = zmq.REQ
            self._ensure_socket()
            
        def request(
            self, 
            message: Union[str, bytes, dict], 
            timeout: int = -1
        ) -> Union[str, bytes]:
            """Send a request and receive the reply.
            
            Args:
                message: Request message
                timeout: Reply timeout in milliseconds (-1 for indefinite)
                
            Returns:
                Union[str, bytes]: Reply message
                
            Raises:
                zmq.Again: If no reply is received within timeout
            """
            if not self._connected:
                raise RuntimeError("Client not connected to an endpoint")
                
            # Prepare message based on its type
            if isinstance(message, dict):
                import json
                message_data = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                message_data = message.encode('utf-8')
            else:
                message_data = message
                
            # Set timeout if specified
            if timeout >= 0:
                old_timeout = self.socket.RCVTIMEO
                self.socket.setsockopt(zmq.RCVTIMEO, timeout)
                
            try:
                # Send request
                self.socket.send(message_data)
                
                # Receive reply
                reply_data = self.socket.recv()
                
                # Try to decode as string, but fall back to bytes if not UTF-8
                try:
                    reply = reply_data.decode('utf-8')
                except UnicodeDecodeError:
                    reply = reply_data
                    
                return reply
                
            finally:
                if timeout >= 0:
                    # Restore original timeout
                    self.socket.setsockopt(zmq.RCVTIMEO, old_timeout)
    
    class ZMQServer(ZMQBase):
        """ZMQ Server pattern.
        
        Implements the reply part of the request-reply pattern.
        """
        
        def __init__(self, context: Optional[zmq.Context] = None):
            """Initialize server.
            
            Args:
                context: ZMQ context to use (creates new one if None)
            """
            super().__init__(context)
            self.socket_type = zmq.REP
            self._ensure_socket()
            
        def receive(self, timeout: int = -1) -> Union[str, bytes]:
            """Receive a request.
            
            Args:
                timeout: Receive timeout in milliseconds (-1 for indefinite)
                
            Returns:
                Union[str, bytes]: Request message
                
            Raises:
                zmq.Again: If no request is received within timeout
            """
            if not self._connected:
                raise RuntimeError("Server not connected to an endpoint")
                
            # Set timeout if specified
            if timeout >= 0:
                old_timeout = self.socket.RCVTIMEO
                self.socket.setsockopt(zmq.RCVTIMEO, timeout)
                
            try:
                # Receive request
                request_data = self.socket.recv()
                
                # Try to decode as string, but fall back to bytes if not UTF-8
                try:
                    request = request_data.decode('utf-8')
                except UnicodeDecodeError:
                    request = request_data
                    
                return request
                
            finally:
                if timeout >= 0:
                    # Restore original timeout
                    self.socket.setsockopt(zmq.RCVTIMEO, old_timeout)
                    
        def reply(self, message: Union[str, bytes, dict]) -> None:
            """Send a reply.
            
            Args:
                message: Reply message
            """
            if not self._connected:
                raise RuntimeError("Server not connected to an endpoint")
                
            # Prepare message based on its type
            if isinstance(message, dict):
                import json
                message_data = json.dumps(message).encode('utf-8')
            elif isinstance(message, str):
                message_data = message.encode('utf-8')
            else:
                message_data = message
                
            # Send reply
            self.socket.send(message_data)

__all__ = [
    "ZMQBase",
    "ZMQPublisher",
    "ZMQSubscriber",
    "ZMQClient",
    "ZMQServer"
]
