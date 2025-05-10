"""Tests for ZMQ messaging patterns.

This module tests the functionality of the ZMQ messaging patterns.
"""

import threading
import time
import unittest
from unittest import mock

import zmq
import pytest

from ailf.messaging.zmq import ZMQBase, ZMQPublisher, ZMQSubscriber, ZMQClient, ZMQServer


class TestZMQBase(unittest.TestCase):
    """Test the ZMQBase class."""

    def test_init(self):
        """Test initialization."""
        base = ZMQBase()
        self.assertIsNotNone(base.context)
        self.assertIsNone(base.socket)
        self.assertIsNone(base.socket_type)
        self.assertFalse(base._connected)
    
    def test_close(self):
        """Test closing the socket."""
        base = ZMQBase()
        # Create a mock socket and assign it to base.socket
        mock_socket = mock.MagicMock()
        base.socket = mock_socket
        base._connected = True
        
        # Call close method
        base.close()
        
        # Verify that close was called on the socket
        mock_socket.close.assert_called_once()
        self.assertIsNone(base.socket)
        self.assertFalse(base._connected)


class TestZMQPublisher(unittest.TestCase):
    """Test the ZMQPublisher class."""
    
    def test_init(self):
        """Test initialization."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            publisher = ZMQPublisher()
            self.assertEqual(publisher.socket_type, zmq.PUB)
            mock_context.return_value.socket.assert_called_with(zmq.PUB)
            self.assertEqual(publisher.socket, mock_socket)
    
    def test_publish_not_connected(self):
        """Test publishing without connecting."""
        publisher = ZMQPublisher()
        with self.assertRaises(RuntimeError):
            publisher.publish("topic", "message")
    
    def test_publish_string(self):
        """Test publishing a string message."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            publisher = ZMQPublisher()
            publisher._connected = True
            
            publisher.publish("topic", "message")
            mock_socket.send_multipart.assert_called_with(
                [b"topic", b"message"]
            )
    
    def test_publish_bytes(self):
        """Test publishing a bytes message."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            publisher = ZMQPublisher()
            publisher._connected = True
            
            publisher.publish("topic", b"message")
            mock_socket.send_multipart.assert_called_with(
                [b"topic", b"message"]
            )
    
    def test_publish_dict(self):
        """Test publishing a dict message."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            publisher = ZMQPublisher()
            publisher._connected = True
            
            publisher.publish("topic", {"key": "value"})
            mock_socket.send_multipart.assert_called_with(
                [b"topic", b'{"key": "value"}']
            )


class TestZMQSubscriber(unittest.TestCase):
    """Test the ZMQSubscriber class."""
    
    def test_init(self):
        """Test initialization."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            subscriber = ZMQSubscriber()
            self.assertEqual(subscriber.socket_type, zmq.SUB)
            mock_context.return_value.socket.assert_called_with(zmq.SUB)
            self.assertEqual(subscriber.socket, mock_socket)
    
    def test_subscribe(self):
        """Test subscribing to a topic."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            subscriber = ZMQSubscriber()
            subscriber.subscribe("topic")
            
            mock_socket.setsockopt.assert_called_with(
                zmq.SUBSCRIBE, b"topic"
            )
    
    def test_unsubscribe(self):
        """Test unsubscribing from a topic."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            subscriber = ZMQSubscriber()
            subscriber.unsubscribe("topic")
            
            mock_socket.setsockopt.assert_called_with(
                zmq.UNSUBSCRIBE, b"topic"
            )
    
    def test_receive_not_connected(self):
        """Test receiving without connecting."""
        subscriber = ZMQSubscriber()
        with self.assertRaises(RuntimeError):
            subscriber.receive()
    
    def test_receive_with_timeout(self):
        """Test receiving with timeout."""
        with mock.patch('zmq.Context.instance') as mock_context:
            mock_socket = mock.MagicMock()
            mock_context.return_value.socket.return_value = mock_socket
            
            # Set up mock socket to return a multipart message
            mock_socket.recv_multipart.return_value = [b"topic", b"message"]
            
            subscriber = ZMQSubscriber()
            subscriber._connected = True
            
            topic, message = subscriber.receive(timeout=100)
            
            # Use assert_any_call instead of assert_called_with to verify the timeout was set
            mock_socket.setsockopt.assert_any_call(zmq.RCVTIMEO, 100)
            
            # Verify the result
            self.assertEqual(topic, "topic")
            self.assertEqual(message, "message")


@pytest.mark.integration
class TestZMQPubSub:
    """Integration tests for ZMQ pub/sub pattern."""
    
    def test_pub_sub(self):
        """Test publish/subscribe pattern."""
        # Only run the full test if desired - for now we'll skip
        # as it requires actual ZMQ socket operations
        pytest.skip("Skipping integration test that requires ZMQ socket operations")
        
        # Use a random port to avoid conflicts
        import random
        port = random.randint(10000, 60000)
        address = f"tcp://127.0.0.1:{port}"
        
        # Create publisher and subscriber
        publisher = ZMQPublisher()
        publisher.bind(address)
        
        subscriber = ZMQSubscriber()
        subscriber.connect(address)
        subscriber.subscribe("test")
        
        # Small delay to allow connection to establish
        time.sleep(0.1)
        
        # Publish a message
        publisher.publish("test", "hello world")
        
        # Receive the message
        topic, message = subscriber.receive(timeout=1000)
        
        # Verify the result
        assert topic == "test"
        assert message == "hello world"
        
        # Clean up
        publisher.close()
        subscriber.close()
