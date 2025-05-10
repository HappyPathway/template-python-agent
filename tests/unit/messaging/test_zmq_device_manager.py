"""Tests for ZMQ Device Manager.

This module tests the functionality of the ZMQ device manager classes.
"""

import threading
import time
import unittest
from unittest import mock

import zmq
import pytest

from ailf.messaging.zmq_device_manager import DeviceManager, DeviceError, create_device
from ailf.messaging.zmq_devices import ZMQDevice, ZMQForwarder, ZMQStreamer, ZMQProxy
from ailf.schemas.zmq_devices import DeviceType


class TestDeviceManager(unittest.TestCase):
    """Test the DeviceManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = DeviceManager()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.manager.stop_all()
    
    def test_create_device_forwarder(self):
        """Test creating a forwarder device."""
        device = self.manager.create_device(
            DeviceType.FORWARDER, 
            "inproc://test-frontend", 
            "inproc://test-backend"
        )
        self.assertIsInstance(device, ZMQForwarder)
        self.assertEqual(len(self.manager._devices), 1)
    
    def test_create_device_streamer(self):
        """Test creating a streamer device."""
        device = self.manager.create_device(
            DeviceType.STREAMER, 
            "inproc://test-frontend", 
            "inproc://test-backend"
        )
        self.assertIsInstance(device, ZMQStreamer)
        self.assertEqual(len(self.manager._devices), 1)
    
    def test_create_device_queue(self):
        """Test creating a queue device."""
        device = self.manager.create_device(
            DeviceType.QUEUE, 
            "inproc://test-frontend", 
            "inproc://test-backend"
        )
        self.assertIsInstance(device, ZMQProxy)
        self.assertEqual(len(self.manager._devices), 1)
    
    def test_create_helper_methods(self):
        """Test helper methods for creating devices."""
        forwarder = self.manager.create_forwarder(
            "inproc://forwarder-front", 
            "inproc://forwarder-back"
        )
        self.assertIsInstance(forwarder, ZMQForwarder)
        
        streamer = self.manager.create_streamer(
            "inproc://streamer-front", 
            "inproc://streamer-back"
        )
        self.assertIsInstance(streamer, ZMQStreamer)
        
        queue = self.manager.create_queue(
            "inproc://queue-front", 
            "inproc://queue-back"
        )
        self.assertIsInstance(queue, ZMQProxy)
        
        self.assertEqual(len(self.manager._devices), 3)
    
    def test_start_device(self):
        """Test starting a device."""
        device = mock.MagicMock(spec=ZMQDevice)
        self.manager.start_device(device)
        
        device.start.assert_called_once()
        self.assertEqual(len(self.manager._devices), 1)
    
    def test_stop_all(self):
        """Test stopping all devices."""
        # Create some mock devices
        devices = [mock.MagicMock(spec=ZMQDevice) for _ in range(3)]
        
        # Add them to the manager
        for device in devices:
            self.manager._devices.append(device)
            
        # Stop all devices
        self.manager.stop_all()
        
        # Verify that stop was called on each device
        for device in devices:
            device.stop.assert_called_once()
        
        # Verify that the devices list was cleared
        self.assertEqual(len(self.manager._devices), 0)
    
    def test_context_manager(self):
        """Test using the manager as a context manager."""
        with self.manager as manager:
            # Create a device
            device = mock.MagicMock(spec=ZMQDevice)
            manager._devices.append(device)
        
        # Verify that stop_all was called
        device.stop.assert_called_once()
        self.assertEqual(len(self.manager._devices), 0)


@pytest.mark.integration
class TestCreateDeviceContextManager(unittest.TestCase):
    """Test the create_device context manager."""
    
    def test_create_device_context_manager(self):
        """Test the create_device context manager."""
        # Use patch to avoid actual ZMQ socket operations
        with mock.patch('ailf.messaging.zmq_device_manager.DeviceManager') as MockManager:
            # Set up the mock manager to return a mock device
            mock_device = mock.MagicMock()
            mock_manager = mock.MagicMock()
            MockManager.return_value = mock_manager
            mock_manager.create_device.return_value = mock_device
            
            # Patch the start method
            mock_device.start = mock.MagicMock()
            mock_device.stop = mock.MagicMock()
            
            # Use the context manager
            with create_device(
                DeviceType.FORWARDER, 
                "inproc://test-frontend", 
                "inproc://test-backend"
            ) as device:
                # Verify the device is what we expect
                self.assertEqual(device, mock_device)
                
                # Verify start was called
                mock_device.start.assert_called_once()
            
            # Verify stop was called
            mock_device.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
