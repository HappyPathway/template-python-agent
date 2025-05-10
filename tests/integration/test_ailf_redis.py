"""Redis Feature Test Script

This script performs a basic functionality test of the Redis components 
in the AILF package. It verifies:

1. Basic Redis operations (get/set)
2. JSON operations
3. PubSub messaging
4. Stream processing
"""

import time
import threading
from queue import Queue
import json

from ailf.messaging.redis import RedisClient, RedisStream, RedisPubSub
from ailf.schemas.redis import RedisConfig

# Store received messages for verification
received_messages = Queue()
processed_stream_items = []


def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)


def test_basic_operations():
    """Test basic Redis operations."""
    print_header("Testing Basic Redis Operations")
    
    client = RedisClient()
    
    # Test connection
    print("Connecting to Redis...")
    is_healthy = client.health_check()
    print(f"Connection healthy: {is_healthy}")
    
    if not is_healthy:
        print("Redis server not available, tests will fail")
        return False
    
    # Test simple set/get
    test_key = "ailf:test:basic"
    test_value = "Hello, Redis!"
    
    client.set(test_key, test_value)
    result = client.get(test_key)
    
    print(f"Set key '{test_key}' to '{test_value}'")
    print(f"Retrieved value: '{result}'")
    print(f"Test passed: {result == test_value}")
    
    # Test JSON operations
    json_key = "ailf:test:json"
    json_value = {
        "name": "AILF Test",
        "version": "0.1.0",
        "features": ["redis", "zmq", "ai"],
        "active": True,
        "metrics": {
            "users": 42,
            "uptime": 99.9
        }
    }
    
    client.set_json(json_key, json_value)
    result = client.get_json(json_key)
    
    print("\nTesting JSON operations:")
    print(f"Set JSON at '{json_key}'")
    print(f"Retrieved JSON: {json.dumps(result, indent=2)}")
    print(f"Test passed: {result == json_value}")
    
    # Clean up
    client.delete(test_key)
    client.delete(json_key)
    
    return True


def message_handler(message):
    """Handle PubSub messages."""
    received_messages.put(message)
    print(f"Received message: {message}")


def test_pubsub():
    """Test Redis PubSub messaging."""
    print_header("Testing Redis PubSub")
    
    # Create subscriber first
    subscriber = RedisPubSub()
    test_channel = "ailf:test:channel"
    
    # Subscribe to test channel
    subscriber.subscribe(test_channel, message_handler)
    print(f"Subscribed to channel: {test_channel}")
    
    # Start subscriber thread
    subscriber.run_in_thread()
    print("Subscriber listening...")
    
    # Give time for subscription to be active
    time.sleep(1)
    
    # Create publisher and send messages
    publisher = RedisPubSub()
    
    # Send test messages
    messages = [
        {"id": 1, "content": "First test message"},
        {"id": 2, "content": "Second test message", "priority": "high"},
        {"id": 3, "content": "Final test message", "metadata": {"source": "test"}}
    ]
    
    for msg in messages:
        publisher.publish(test_channel, msg)
        print(f"Published: {msg}")
        time.sleep(0.5)
    
    # Wait for messages to be received
    print("Waiting for messages to be processed...")
    time.sleep(2)
    
    # Check results
    received = []
    while not received_messages.empty():
        received.append(received_messages.get())
    
    print(f"\nSent {len(messages)} messages, received {len(received)}")
    print(f"All messages received: {len(messages) == len(received)}")
    
    # Stop subscriber
    subscriber.stop()
    print("Subscriber stopped")
    
    return len(messages) == len(received)


def stream_consumer(stream_name, group, consumer):
    """Consumer thread for stream testing."""
    stream = RedisStream(stream_name)
    
    # Create consumer group if needed
    try:
        stream.create_consumer_group(group, consumer)
    except Exception:
        # Group may already exist
        pass
        
    print(f"Consumer {consumer} started")
    
    # Process messages for 5 seconds
    end_time = time.time() + 5
    
    while time.time() < end_time:
        messages = stream.read_group(count=5, block=500)
        
        for message in messages:
            msg_id = message["id"]
            data = message["data"]
            
            print(f"Consumer {consumer} processing: {data}")
            processed_stream_items.append(data)
            
            # Acknowledge message
            stream.acknowledge(msg_id)
            
        time.sleep(0.1)
    
    print(f"Consumer {consumer} finished")


def test_streams():
    """Test Redis Streams."""
    print_header("Testing Redis Streams")
    
    stream_name = "ailf:test:stream"
    group_name = "test-group"
    
    # Create producer
    producer = RedisStream(stream_name)
    
    # Start consumer threads
    consumers = []
    for i in range(2):
        consumer = threading.Thread(
            target=stream_consumer,
            args=(stream_name, group_name, f"consumer-{i}")
        )
        consumer.start()
        consumers.append(consumer)
    
    # Give consumers time to connect
    time.sleep(1)
    
    # Produce items
    items_to_produce = 10
    for i in range(items_to_produce):
        item = {
            "id": i,
            "name": f"Item {i}",
            "timestamp": time.time()
        }
        msg_id = producer.add(item)
        print(f"Produced item {i}, ID: {msg_id}")
        time.sleep(0.2)
    
    # Wait for consumers to finish
    for consumer in consumers:
        consumer.join()
    
    # Check results
    print(f"\nProduced {items_to_produce} items")
    print(f"Processed {len(processed_stream_items)} items")
    print(f"Test passed: {len(processed_stream_items) == items_to_produce}")
    
    return len(processed_stream_items) == items_to_produce


def run_all_tests():
    """Run all Redis tests."""
    results = {}
    
    # Test basic operations
    results["basic"] = test_basic_operations()
    
    if not results["basic"]:
        print("\nSkipping remaining tests due to Redis connection issue.")
        return results
    
    # Test PubSub
    results["pubsub"] = test_pubsub()
    
    # Test Streams
    results["streams"] = test_streams()
    
    # Print overall results
    print_header("Test Results")
    for test, passed in results.items():
        print(f"{test.ljust(10)}: {'✅ PASSED' if passed else '❌ FAILED'}")
    
    return results


if __name__ == "__main__":
    print("AILF Redis Feature Test")
    print("======================")
    
    try:
        results = run_all_tests()
        all_passed = all(results.values())
        
        if all_passed:
            print("\nAll tests passed! The Redis implementation is working correctly.")
        else:
            print("\nSome tests failed. Please check the logs for details.")
    except Exception as e:
        print(f"\nTest error: {str(e)}")
        import traceback
        traceback.print_exc()
