"""
ZeroMQ Device Example
=====================

This example demonstrates how to use the ZeroMQ devices and device manager 
to set up publish/subscribe messaging with multiple publishers and subscribers.

The example sets up:
1. A forwarder device to distribute messages
2. Multiple publishers sending messages to the forwarder
3. Multiple subscribers receiving from the forwarder

Usage:
    Run this script directly to see example in action.
"""

import time
import threading
from typing import List, Optional

import zmq

from ailf.messaging.zmq import (  # Changed from ailf.messaging
    DeviceManager, 
    ZMQPublisher, 
    ZMQSubscriber, 
    create_device
)


class SimplePublisher:
    """Simple publisher that sends messages to a ZMQ forwarder."""
    
    def __init__(self, 
                 name: str, 
                 connect_addr: str, 
                 topic: str = "news",
                 context: Optional[zmq.Context] = None):
        self.name = name
        self.topic = topic
        self.running = False
        self.publisher = ZMQPublisher(context)
        self.publisher.connect(connect_addr)
        self._thread = None
        
    def start(self):
        """Start publishing messages in a background thread."""
        self.running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
        
    def stop(self):
        """Stop the publisher."""
        self.running = False
        if self._thread:
            self._thread.join(1.0)
            
    def _run(self):
        """Run the publisher loop."""
        counter = 0
        while self.running:
            counter += 1
            message = f"{self.topic} update {counter} from {self.name}"
            self.publisher.publish(self.topic, message)
            print(f"[{self.name}] Published: {message}")
            time.sleep(0.5)


class SimpleSubscriber:
    """Simple subscriber that receives messages from a ZMQ forwarder."""
    
    def __init__(self, 
                 name: str, 
                 connect_addr: str, 
                 topics: List[str] = None,
                 context: Optional[zmq.Context] = None):
        self.name = name
        self.topics = topics or ["news"]
        self.running = False
        self.subscriber = ZMQSubscriber(context)
        self.subscriber.connect(connect_addr)
        for topic in self.topics:
            self.subscriber.subscribe(topic)
        self._thread = None
        
    def start(self):
        """Start receiving messages in a background thread."""
        self.running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
        
    def stop(self):
        """Stop the subscriber."""
        self.running = False
        if self._thread:
            self._thread.join(1.0)
            
    def _run(self):
        """Run the subscriber loop."""
        while self.running:
            try:
                topic, message = self.subscriber.receive(timeout=100)
                if topic:
                    print(f"[{self.name}] Received: {message}")
            except zmq.Again:
                # No message available within timeout
                pass
            except Exception as e:
                print(f"[{self.name}] Error: {str(e)}")
                time.sleep(0.1)


def run_context_manager_example():
    """Run an example using the context manager approach."""
    print("\nStarting example with context manager...\n")
    
    # Use context manager to create and manage forwarder device
    with create_device(
        "FORWARDER", 
        "tcp://127.0.0.1:5555",  # Frontend (SUB)
        "tcp://127.0.0.1:5556"   # Backend (PUB)
    ) as device:
        # Create publishers
        publishers = [
            SimplePublisher(f"Publisher-{i}", "tcp://127.0.0.1:5555")
            for i in range(2)
        ]
        
        # Create subscribers with different topic subscriptions
        subscribers = [
            SimpleSubscriber(f"Subscriber-{i}", "tcp://127.0.0.1:5556", ["news"])
            for i in range(3)
        ]
        
        # Start all publishers and subscribers
        for pub in publishers:
            pub.start()
        for sub in subscribers:
            sub.start()
            
        try:
            # Run for a while
            print("Running for 5 seconds...")
            time.sleep(5)
        finally:
            # Clean up
            for pub in publishers:
                pub.stop()
            for sub in subscribers:
                sub.stop()
    
    print("Context manager example completed.\n")


def run_device_manager_example():
    """Run an example using the DeviceManager class."""
    print("\nStarting example with DeviceManager...\n")
    
    # Create device manager
    manager = DeviceManager()
    
    try:
        # Create a forwarder device
        forwarder = manager.create_forwarder(
            "tcp://127.0.0.1:5557",  # Frontend (SUB)
            "tcp://127.0.0.1:5558"   # Backend (PUB)
        )
        
        # Start the device
        forwarder.start()
        
        # Create publishers
        publishers = [
            SimplePublisher(f"Manager-Pub-{i}", "tcp://127.0.0.1:5557", 
                           topic=("tech" if i % 2 else "news"))
            for i in range(3)
        ]
        
        # Create subscribers with different topic subscriptions
        subscribers = [
            SimpleSubscriber(f"Manager-Sub-{i}", "tcp://127.0.0.1:5558", 
                            topics=(["tech"] if i % 3 == 0 else 
                                   ["news"] if i % 3 == 1 else
                                   ["tech", "news"]))
            for i in range(4)
        ]
        
        # Start all publishers and subscribers
        for pub in publishers:
            pub.start()
        for sub in subscribers:
            sub.start()
            
        # Run for a while
        print("Running for 5 seconds...")
        time.sleep(5)
        
    finally:
        # Clean up publishers and subscribers
        for pub in publishers:
            pub.stop()
        for sub in subscribers:
            sub.stop()
        
        # Clean up devices
        manager.stop_all()
    
    print("DeviceManager example completed.\n")


if __name__ == "__main__":
    print("ZeroMQ Device Examples")
    print("====================\n")
    
    # Run examples
    run_context_manager_example()
    run_device_manager_example()
    
    print("\nAll examples completed.")
