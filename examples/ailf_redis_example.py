"""
Redis Messaging Example
======================

This example demonstrates how to use the Redis messaging components
in the AILF package for pub/sub and stream-based messaging.

The example demonstrates:
1. Basic Redis operations
2. Publishing and subscribing to messages using RedisPubSub
3. Working with Redis Streams

Prerequisites:
- Redis server running on localhost:6379 (or set env var REDIS_HOST and REDIS_PORT)
"""

import os
import time
import threading
import json
from typing import Dict, Any

from ailf.messaging import RedisClient, RedisPubSub, RedisStream, RedisConfig


def demo_basic_redis_operations():
    """Demonstrate basic Redis operations."""
    print("\n=== Basic Redis Operations ===")
    
    # Get Redis configuration from environment variables or use defaults
    config = RedisConfig(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=0
    )
    
    # Create Redis client
    try:
        client = RedisClient(config)
        
        # Store a value
        key = "ailf:example:greeting"
        client.set(key, "Hello from AILF!")
        print(f"Stored value at {key}")
        
        # Retrieve the value
        value = client.get(key)
        print(f"Retrieved value: {value}")
        
        # Store a JSON value
        json_key = "ailf:example:user"
        user_data = {
            "name": "AI Agent",
            "role": "assistant",
            "skills": ["reasoning", "coding", "learning"],
            "active": True,
            "created_at": time.time()
        }
        client.set_json(json_key, user_data)
        print(f"Stored JSON data at {json_key}")
        
        # Retrieve the JSON value
        retrieved_data = client.get_json(json_key)
        print(f"Retrieved JSON data: {json.dumps(retrieved_data, indent=2)}")
        
        # Clean up
        client.delete(key)
        client.delete(json_key)
        print("Cleaned up Redis keys")
        
    except Exception as e:
        print(f"Error in Redis operations: {str(e)}")


def message_handler(message: Dict[str, Any]):
    """Handle incoming Redis pub/sub messages."""
    print(f"Received message: {json.dumps(message, indent=2)}")


def demo_redis_pubsub():
    """Demonstrate Redis pub/sub messaging."""
    print("\n=== Redis Pub/Sub Messaging ===")
    
    # Get Redis configuration from environment variables or use defaults
    config = RedisConfig(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=0
    )
    
    try:
        # Create subscriber
        subscriber = RedisPubSub(RedisClient(config))
        
        # Subscribe to channel
        channel = "ailf:example:notifications"
        subscriber.subscribe(channel, message_handler)
        print(f"Subscribed to {channel}")
        
        # Start listener in a thread
        thread = subscriber.run_in_thread()
        print("Subscriber thread started")
        
        # Create publisher
        publisher = RedisPubSub(RedisClient(config))
        
        # Publish some messages
        for i in range(3):
            message = {
                "id": i,
                "type": "notification",
                "content": f"Test message {i}",
                "timestamp": time.time()
            }
            publisher.publish(channel, message)
            print(f"Published message {i}")
            time.sleep(0.5)
            
        # Wait for messages to be processed
        print("Waiting for messages to be processed...")
        time.sleep(1)
        
        # Clean up
        subscriber.stop()
        print("Subscriber stopped")
        
    except Exception as e:
        print(f"Error in Redis pub/sub: {str(e)}")


def stream_processor(stream: RedisStream, consumer_group: str, consumer_id: str):
    """Process messages from a Redis stream."""
    # Create consumer group if it doesn't exist
    stream.create_consumer_group(consumer_group, consumer_id)
    print(f"Consumer {consumer_id} ready")
    
    # Process messages
    processed_count = 0
    while processed_count < 5:  # Process 5 messages then stop
        messages = stream.read_group(count=1, block=1000)  # Block for 1 second
        
        if not messages:
            continue
            
        for message in messages:
            msg_id = message["id"]
            data = message["data"]
            
            print(f"Consumer {consumer_id} processing message {msg_id}: {data}")
            
            # Simulate processing
            time.sleep(0.2)
            
            # Acknowledge message
            stream.acknowledge(msg_id)
            print(f"Consumer {consumer_id} acknowledged message {msg_id}")
            
            processed_count += 1
    
    print(f"Consumer {consumer_id} finished processing")


def demo_redis_streams():
    """Demonstrate Redis streams."""
    print("\n=== Redis Streams ===")
    
    # Get Redis configuration from environment variables or use defaults
    config = RedisConfig(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=0
    )
    
    try:
        # Create stream
        stream_name = "ailf:example:tasks"
        producer_stream = RedisStream(stream_name, RedisClient(config))
        print(f"Created stream: {stream_name}")
        
        # Prepare consumer group
        group_name = "example-consumers"
        
        # Start two consumers in separate threads
        consumer1_stream = RedisStream(stream_name, RedisClient(config))
        consumer2_stream = RedisStream(stream_name, RedisClient(config))
        
        consumer1_thread = threading.Thread(
            target=stream_processor, 
            args=(consumer1_stream, group_name, "consumer-1")
        )
        consumer2_thread = threading.Thread(
            target=stream_processor, 
            args=(consumer2_stream, group_name, "consumer-2")
        )
        
        consumer1_thread.start()
        consumer2_thread.start()
        
        # Give consumers time to set up
        time.sleep(1)
        
        # Produce messages
        for i in range(10):  # Send 10 messages
            task_data = {
                "task_id": i,
                "type": "processing",
                "priority": i % 3,  # 0, 1, 2
                "data": f"Task payload {i}",
                "created_at": time.time()
            }
            
            msg_id = producer_stream.add(task_data)
            print(f"Added task {i} to stream, ID: {msg_id}")
            time.sleep(0.1)
        
        # Wait for consumers to finish
        consumer1_thread.join()
        consumer2_thread.join()
        print("All consumers finished")
        
    except Exception as e:
        print(f"Error in Redis streams: {str(e)}")


if __name__ == "__main__":
    print("Redis Messaging Example")
    print("======================")
    
    # Check if Redis is available
    try:
        check_client = RedisClient()
        if check_client.health_check():
            print("Redis server is available!")
            demo_basic_redis_operations()
            demo_redis_pubsub()
            demo_redis_streams()
        else:
            print("Redis server not available. Make sure Redis is running on localhost:6379")
            print("Or set environment variables REDIS_HOST and REDIS_PORT")
    except Exception as e:
        print(f"Error connecting to Redis: {str(e)}")
        print("Make sure Redis is running or install the redis Python package")
    
    print("\nExample completed")
