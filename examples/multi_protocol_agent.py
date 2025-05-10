"""Multi-Protocol Agent Communication Example.

This example demonstrates how to build agents that can communicate through
multiple messaging protocols (Redis and ZMQ) depending on the use case.

This pattern is useful for:
1. Hybrid environments where some components only support certain protocols
2. Gradual migration from one messaging system to another
3. Optimizing for different communication patterns (pub/sub vs. req/rep)

Example:
    $ python -m examples.multi_protocol_agent

Requirements:
    - Redis server running locally
    - Python packages: pyzmq, redis
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time

from ailf.messaging.zmq import (DeviceType, SocketType, ZMQDevice, ZMQManager, 
                             ZMQSocket)
from ailf.messaging.redis import RedisClient, RedisPubSub, RedisStream

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("multi_protocol_agent")


class ZMQClient:
    """Client for ZMQ messaging patterns.

    This class provides a simplified interface for working with ZMQ patterns
    (pub/sub, request/reply) in a way that fits the agent communication pattern.
    """

    def __init__(self):
        """Initialize the ZMQ client."""
        self.manager = ZMQManager()
        self.manager.__enter__()  # Enter the context manually

        # Socket references
        self.publisher = None
        self.subscriber = None
        self.requester = None
        self.responder = None

        # Subscriber topic mapping
        self.subscriber_topics = []
        self.subscriber_callback = None

        # For monitoring subscriber socket
        self._subscriber_running = False
        self._subscriber_thread = None

    def setup_publisher(self, address: str) -> None:
        """Set up a publisher socket.

        Args:
            address: The address to bind to (e.g., "tcp://*:5555")
        """
        logger.info("Setting up publisher on %s", address)
        self.publisher = self.manager.socket(
            SocketType.PUB, address, bind=True).__enter__()

    def add_subscriber(self, address: str, topic: str) -> None:
        """Add a subscription.

        Args:
            address: The address to connect to (e.g., "tcp://localhost:5555")
            topic: The topic to subscribe to
        """
        logger.info("Setting up subscriber to %s on topic %s", address, topic)
        self.subscriber = self.manager.socket(
            SocketType.SUB, address, bind=False, topics=[topic]).__enter__()
        self.subscriber_topics.append(topic)

        # Start subscriber thread if not already running
        self._start_subscriber_thread()

    def setup_request(self, address: str) -> None:
        """Set up a request socket.

        Args:
            address: The address to connect to (e.g., "tcp://localhost:5556")
        """
        logger.info("Setting up request socket on %s", address)
        self.requester = self.manager.socket(
            SocketType.REQ, address, bind=False).__enter__()

    def setup_reply(self, address: str) -> None:
        """Set up a reply socket.

        Args:
            address: The address to bind to (e.g., "tcp://*:5556")
        """
        logger.info("Setting up reply socket on %s", address)
        self.responder = self.manager.socket(
            SocketType.REP, address, bind=True).__enter__()

    def publish(self, topic: str, message: str) -> None:
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to
            message: The message to publish
        """
        if not self.publisher:
            raise ValueError("Publisher socket not set up")

        logger.debug("Publishing message to topic %s: %s", topic, message)
        self.publisher.send_message(message, topic=topic)

    def _start_subscriber_thread(self) -> None:
        """Start the subscriber thread if not already running."""
        if not self._subscriber_running and self.subscriber:
            self._subscriber_running = True
            self._subscriber_thread = threading.Thread(
                target=self._subscriber_loop, daemon=True)
            self._subscriber_thread.start()

    def _subscriber_loop(self) -> None:
        """Background thread for receiving subscription messages."""
        logger.info("Subscriber thread started")
        while self._subscriber_running:
            # Receive messages with a timeout
            self.receive(timeout=100)
            time.sleep(0.01)  # Avoid busy-waiting

    def receive(self, timeout: int = None) -> None:
        """Receive and process messages from subscription.

        Args:
            timeout: Receive timeout in milliseconds
        """
        if not self.subscriber:
            return

        # Receive message
        message = self.subscriber.receive(timeout=timeout)
        if message:
            topic = message.topic
            payload = message.payload

            # Call the subscriber callback if set
            if self.subscriber_callback:
                try:
                    self.subscriber_callback(topic, payload)
                except Exception as e:
                    logger.error("Error in subscriber callback: %s", str(e))

    def request(self, message: str, timeout: int = 5000) -> str:
        """Send a request and wait for a reply.

        Args:
            message: The request message
            timeout: Request timeout in milliseconds

        Returns:
            The reply message
        """
        if not self.requester:
            raise ValueError("Request socket not set up")

        # Send request
        logger.debug("Sending request: %s", message)
        self.requester.send_message(message)

        # Receive reply
        reply = self.requester.receive(timeout=timeout)
        if reply:
            logger.debug("Received reply: %s", reply.payload)
            return reply.payload
        else:
            logger.warning("No reply received within timeout")
            return None

    def receive_request(self, timeout: int = 1000) -> str:
        """Receive a request on the reply socket.

        Args:
            timeout: Receive timeout in milliseconds

        Returns:
            The request message or None if timeout
        """
        if not self.responder:
            raise ValueError("Reply socket not set up")

        # Receive request
        request = self.responder.receive(timeout=timeout)
        if request:
            logger.debug("Received request: %s", request.payload)
            return request.payload
        return None

    def send_reply(self, message: str) -> None:
        """Send a reply to a received request.

        Args:
            message: The reply message
        """
        if not self.responder:
            raise ValueError("Reply socket not set up")

        logger.debug("Sending reply: %s", message)
        self.responder.send_message(message)

    def close(self) -> None:
        """Close all sockets and the ZMQ context."""
        logger.info("Closing ZMQ client")

        # Stop subscriber thread if running
        self._subscriber_running = False
        if self._subscriber_thread:
            self._subscriber_thread.join(timeout=1.0)

        # Close all sockets
        for socket in [self.publisher, self.subscriber, self.requester, self.responder]:
            if socket:
                try:
                    socket.__exit__(None, None, None)
                except Exception as e:
                    logger.error("Error closing socket: %s", str(e))

        # Close ZMQ manager
        try:
            self.manager.__exit__(None, None, None)
        except Exception as e:
            logger.error("Error closing ZMQ manager: %s", str(e))


class HybridMessagingAgent:
    """Agent that can communicate via both Redis and ZMQ."""

    def __init__(self, agent_id: str):
        """Initialize the agent.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self.running = False

        # Initialize Redis clients
        self.redis_client = RedisClient()
        self.redis_pubsub = RedisPubSub(self.redis_client)
        self.redis_stream = RedisStream(
            "hybrid_agent_tasks", self.redis_client)

        # Initialize ZMQ client
        self.zmq_client = ZMQClient()

        # Set up signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        """Handle termination signals."""
        logger.info("Received signal %s, shutting down...", signum)
        self.running = False
        # Give background threads time to complete
        time.sleep(0.5)
        sys.exit(0)

    def start(self):
        """Start the agent."""
        self.running = True
        logger.info("Agent %s started", self.agent_id)

        # Subscribe to Redis channels
        self.redis_pubsub.subscribe("broadcast", self._handle_redis_broadcast)
        self.redis_pubsub.run_in_thread()

        # Setup Redis Stream consumer group
        try:
            self.redis_stream.create_consumer_group("agents", self.agent_id)
        except Exception as e:
            logger.warning("Error creating consumer group: %s", str(e))

        # Start ZMQ sockets
        self.zmq_client.add_subscriber("tcp://localhost:5555", "updates")
        self.zmq_client.subscriber_callback = self._handle_zmq_message

        # Set up request socket
        self.zmq_client.setup_request("tcp://localhost:5556")

        return self

    def run(self):
        """Run the agent's main loop."""
        try:
            while self.running:
                # Process ZMQ messages
                self.zmq_client.receive(timeout=100)  # Non-blocking

                # Process Redis stream messages
                messages = self.redis_stream.read_group(count=5, block=500)
                for message in messages:
                    try:
                        self._process_task(message["data"])
                        self.redis_stream.acknowledge(message["id"])
                    except Exception as e:
                        logger.error("Error processing message: %s", str(e))

                time.sleep(0.1)  # Small sleep to prevent CPU spinning
        finally:
            self.stop()

    def stop(self):
        """Stop the agent."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping agent %s", self.agent_id)

        # Clean up Redis connections
        self.redis_pubsub.stop()

        # Clean up ZMQ connections
        self.zmq_client.close()

    def _handle_redis_broadcast(self, message):
        """Handle broadcast messages from Redis pub/sub.

        Args:
            message: The received message data
        """
        logger.info("Redis broadcast received: %s", message)

        # Process the message based on its type
        if isinstance(message, dict) and "type" in message:
            if message["type"] == "command":
                self._execute_command(message["command"], source="redis")

    def _handle_zmq_message(self, topic, message):
        """Handle messages from ZMQ subscription.

        Args:
            topic: The topic the message was published on
            message: The received message data
        """
        logger.info("ZMQ message received on topic %s", topic)

        # Try to parse JSON if it's a string
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                pass

        # Process the message based on its type
        if isinstance(message, dict) and "type" in message:
            if message["type"] == "command":
                self._execute_command(message["command"], source="zmq")

    def _execute_command(self, command: str, source: str):
        """Execute a command received from any messaging system.

        Args:
            command: The command to execute
            source: The source of the command (redis or zmq)
        """
        logger.info("Executing command from %s: %s", source, command)

        # Implement command execution logic
        if command == "ping":
            # Respond with pong over the same protocol
            if source == "redis":
                self.redis_pubsub.publish("responses", {
                    "from": self.agent_id,
                    "type": "response",
                    "response": "pong"
                })
            elif source == "zmq":
                response = json.dumps({
                    "from": self.agent_id,
                    "type": "response",
                    "response": "pong"
                })
                self.zmq_client.publish("responses", response)

    def _process_task(self, task):
        """Process a task from the Redis stream.

        Args:
            task: Task data from Redis stream
        """
        logger.info("Processing task: %s", task)

        # Example of sending a ZMQ request based on Redis task
        if "action" in task and task["action"] == "query":
            response = self.zmq_client.request(task["query"])

            # Store the result back in Redis
            self.redis_client.set_json(
                f"result:{task['id']}",
                {"query": task["query"], "response": response}
            )

            logger.info("Task %s completed", task['id'])


def send_test_messages():
    """Send some test messages through both protocols."""
    # Send Redis pub/sub message
    pubsub = RedisPubSub()
    pubsub.publish("broadcast", {
        "type": "command",
        "command": "ping",
        "timestamp": time.time()
    })

    # Send Redis stream message
    stream = RedisStream("hybrid_agent_tasks")
    stream.add({
        "id": f"task-{int(time.time())}",
        "action": "query",
        "query": "test_query",
        "timestamp": str(time.time())
    })

    # Send ZMQ pub/sub message
    zmq_client = ZMQClient()
    zmq_client.setup_publisher("tcp://*:5555")
    zmq_client.publish("updates", json.dumps({
        "type": "command",
        "command": "ping",
        "timestamp": time.time()
    }))

    # Clean up
    zmq_client.close()


def setup_zmq_responder():
    """Set up a ZMQ responder for testing."""
    def responder_thread():
        zmq_client = ZMQClient()
        zmq_client.setup_reply("tcp://*:5556")

        while True:
            try:
                request = zmq_client.receive_request()
                if request:
                    # Echo the request as a response
                    zmq_client.send_reply(f"Response to: {request}")
            except KeyboardInterrupt:
                break

        zmq_client.close()

    threading.Thread(target=responder_thread, daemon=True).start()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-protocol agent example")
    parser.add_argument(
        "--id",
        default=f"agent-{int(time.time())}",
        help="Agent ID"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send test messages"
    )

    args = parser.parse_args()

    if args.test:
        send_test_messages()
        return

    # Set up ZMQ responder in background thread
    setup_zmq_responder()

    # Start the agent
    agent = HybridMessagingAgent(args.id).start()

    try:
        # Send some test messages after a short delay
        def delayed_test():
            time.sleep(2)  # Give the agent time to set up
            send_test_messages()

        threading.Thread(target=delayed_test, daemon=True).start()

        # Run the agent
        agent.run()
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    main()
