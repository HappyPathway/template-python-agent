"""Redis-based Agent Communication Example.

This example demonstrates how to use Redis PubSub for agent communication.
It creates two agents, a publisher and a subscriber, that communicate
through Redis channels.

Example:
    Run the publisher in one terminal:
    $ python -m examples.redis_pubsub_example --role publisher

    Run the subscriber in another terminal:
    $ python -m examples.redis_pubsub_example --role subscriber
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from ailf.messaging.redis import RedisConfig, RedisPubSub

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("redis_agent")

# Define channels
COMMAND_CHANNEL = "agents:commands"
RESPONSE_CHANNEL = "agents:responses"
STATUS_CHANNEL = "agents:status"


class BaseAgent:
    """Base agent with Redis communication capabilities."""

    def __init__(self, agent_id: str, redis_config: Optional[RedisConfig] = None):
        """Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent
            redis_config: Optional Redis configuration
        """
        self.agent_id = agent_id
        self.redis_config = redis_config or RedisConfig()
        self.pubsub = RedisPubSub()
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up handlers for termination signals."""
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        # Give the background threads time to complete
        time.sleep(0.5)
        sys.exit(0)

    def publish_status(self, status: str, details: Dict = None):
        """Publish agent status update.

        Args:
            status: Status message
            details: Additional status details
        """
        message = {
            "agent_id": self.agent_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.pubsub.publish(STATUS_CHANNEL, message)
        logger.debug(f"Published status: {status}")

    def start(self):
        """Start the agent."""
        self.running = True
        self.publish_status("starting")
        logger.info(f"Agent {self.agent_id} started")

    def stop(self):
        """Stop the agent."""
        self.running = False
        self.publish_status("stopping")
        logger.info(f"Agent {self.agent_id} stopped")


class PublisherAgent(BaseAgent):
    """Agent that publishes commands to other agents."""

    def __init__(self, agent_id: str, redis_config: Optional[RedisConfig] = None):
        """Initialize the publisher agent.

        Args:
            agent_id: Unique identifier for this agent
            redis_config: Optional Redis configuration
        """
        super().__init__(agent_id, redis_config)
        self.response_handlers = {}

        # Subscribe to responses
        self.pubsub.subscribe(RESPONSE_CHANNEL, self._handle_response)
        self.pubsub_thread = None

    def _handle_response(self, message: Dict[str, Any]):
        """Handle responses from other agents.

        Args:
            message: Response message
        """
        if not isinstance(message, dict):
            logger.warning(f"Received non-dict message: {message}")
            return

        request_id = message.get("request_id")
        source_agent = message.get("agent_id")

        logger.info(
            f"Received response from {source_agent} for request {request_id}")
        logger.info(
            f"Response data: {json.dumps(message.get('data', {}), indent=2)}")

    def send_command(self, command: str, target_agent: str = None, data: Dict = None):
        """Send a command to other agents.

        Args:
            command: Command to send
            target_agent: Optional target agent ID (None for broadcast)
            data: Command data

        Returns:
            Request ID
        """
        import uuid
        request_id = str(uuid.uuid4())

        message = {
            "request_id": request_id,
            "agent_id": self.agent_id,
            "target_agent": target_agent,
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }

        self.pubsub.publish(COMMAND_CHANNEL, message)
        logger.info(f"Sent command '{command}' with request ID {request_id}")
        return request_id

    def start(self):
        """Start the publisher agent."""
        super().start()
        self.pubsub_thread = self.pubsub.run_in_thread()

        # Demo loop: Send a command every few seconds
        try:
            while self.running:
                self.send_command(
                    "ping", data={"message": "Hello from publisher!"})
                time.sleep(3)

                self.send_command("process", data={
                    "task_id": "task-123",
                    "priority": "high",
                    "parameters": {
                        "max_tokens": 1024,
                        "temperature": 0.7
                    }
                })
                time.sleep(5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the publisher agent."""
        super().stop()
        self.pubsub.stop()


class SubscriberAgent(BaseAgent):
    """Agent that subscribes to and processes commands."""

    def __init__(self, agent_id: str, redis_config: Optional[RedisConfig] = None):
        """Initialize the subscriber agent.

        Args:
            agent_id: Unique identifier for this agent
            redis_config: Optional Redis configuration
        """
        super().__init__(agent_id, redis_config)

        # Register command handlers
        self.command_handlers = {
            "ping": self._handle_ping,
            "process": self._handle_process,
            "stop": self._handle_stop
        }

        # Subscribe to commands
        self.pubsub.subscribe(COMMAND_CHANNEL, self._handle_command)
        self.pubsub_thread = None

    def _handle_command(self, message: Dict[str, Any]):
        """Process incoming commands.

        Args:
            message: Command message
        """
        if not isinstance(message, dict):
            logger.warning(f"Received non-dict message: {message}")
            return

        command = message.get("command")
        source_agent = message.get("agent_id")
        request_id = message.get("request_id")
        target_agent = message.get("target_agent")

        # Check if this command is for us or for everyone
        if target_agent and target_agent != self.agent_id:
            return

        logger.info(f"Received command '{command}' from {source_agent}")

        # Find and execute the appropriate handler
        handler = self.command_handlers.get(command)
        if handler:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error handling command '{command}': {str(e)}")
                self._send_response(request_id, source_agent, {
                    "error": str(e),
                    "status": "error"
                })
        else:
            logger.warning(f"Unknown command: {command}")
            self._send_response(request_id, source_agent, {
                "error": f"Unknown command: {command}",
                "status": "error"
            })

    def _send_response(self, request_id: str, target_agent: str, data: Dict):
        """Send a response to a command.

        Args:
            request_id: Original request ID
            target_agent: Agent ID to respond to
            data: Response data
        """
        message = {
            "request_id": request_id,
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        self.pubsub.publish(RESPONSE_CHANNEL, message)
        logger.debug(f"Sent response for request {request_id}")

    def _handle_ping(self, message: Dict[str, Any]):
        """Handle ping command.

        Args:
            message: Command message
        """
        request_id = message.get("request_id")
        source_agent = message.get("agent_id")

        logger.info(f"Handling ping from {source_agent}")

        # Send a response
        self._send_response(request_id, source_agent, {
            "message": "Pong!",
            "status": "success",
            "agent_info": {
                "id": self.agent_id,
                "uptime": time.time()
            }
        })

    def _handle_process(self, message: Dict[str, Any]):
        """Handle process command.

        Args:
            message: Command message
        """
        request_id = message.get("request_id")
        source_agent = message.get("agent_id")
        data = message.get("data", {})

        task_id = data.get("task_id", "unknown")
        priority = data.get("priority", "normal")

        logger.info(f"Processing task {task_id} with priority {priority}")

        # Simulate some processing time
        time.sleep(1)

        # Send a response
        self._send_response(request_id, source_agent, {
            "task_id": task_id,
            "result": {
                "status": "completed",
                "processing_time": "1.0s",
                "output": f"Processed task {task_id} with priority {priority}"
            }
        })

    def _handle_stop(self, message: Dict[str, Any]):
        """Handle stop command.

        Args:
            message: Command message
        """
        request_id = message.get("request_id")
        source_agent = message.get("agent_id")

        logger.info(f"Received stop command from {source_agent}")

        # Send acknowledgement before stopping
        self._send_response(request_id, source_agent, {
            "status": "stopping",
            "message": f"Agent {self.agent_id} is shutting down"
        })

        # Stop the agent
        threading.Timer(1, self.stop).start()

    def start(self):
        """Start the subscriber agent."""
        super().start()
        self.pubsub_thread = self.pubsub.run_in_thread()

        # Keep the main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the subscriber agent."""
        super().stop()
        self.pubsub.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Redis Agent Communication Example")
    parser.add_argument("--role", choices=["publisher", "subscriber"], required=True,
                        help="Agent role (publisher or subscriber)")
    parser.add_argument("--id", default=None, help="Agent ID (optional)")
    args = parser.parse_args()

    # Generate a default ID based on role if not provided
    import socket
    import uuid

    if not args.id:
        if args.role == "publisher":
            args.id = f"publisher-{socket.gethostname()}"
        else:
            args.id = f"subscriber-{str(uuid.uuid4())[:8]}"

    # Create and start the appropriate agent
    if args.role == "publisher":
        agent = PublisherAgent(args.id)
    else:
        agent = SubscriberAgent(args.id)

    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    main()
