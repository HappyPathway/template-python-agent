"""
Redis-Based Agent Communication Example
======================================

This example demonstrates how to build a multi-agent system using Redis for communication.

We'll build a simple pipeline with three agents:
1. Producer Agent: Generates tasks to be processed
2. Worker Agent: Processes tasks and produces results
3. Monitor Agent: Monitors the system and reports statistics

The agents communicate via:
- Redis Streams for task distribution
- Redis PubSub for system-wide announcements
- Redis key-value for shared state
"""

import json
import time
import random
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable

from ailf.messaging.redis import RedisClient, RedisStream, RedisPubSub


# Define agent states
AGENT_STATE_STARTING = "starting"
AGENT_STATE_RUNNING = "running"
AGENT_STATE_PAUSED = "paused"
AGENT_STATE_STOPPED = "stopped"
AGENT_STATE_ERROR = "error"


@dataclass
class AgentStats:
    """Agent statistics."""
    messages_processed: int = 0
    messages_produced: int = 0
    errors: int = 0
    last_processed: Optional[float] = None
    last_error: Optional[str] = None


class BaseAgent:
    """Base agent class with Redis communication capabilities."""
    
    def __init__(self, agent_id: str, agent_type: str):
        """Initialize the agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent (e.g., "producer", "worker", "monitor")
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = AGENT_STATE_STARTING
        self.stats = AgentStats()
        self.running = False
        
        # Set up Redis connections
        self.redis = RedisClient()
        self.pubsub = RedisPubSub()
        
        # Register system-wide announcements handler
        self.pubsub.subscribe("system:announcements", self._handle_announcement)
        
        # Save agent info to Redis
        self._update_agent_info()
    
    def _update_agent_info(self) -> None:
        """Update agent information in Redis."""
        agent_info = {
            "id": self.agent_id,
            "type": self.agent_type,
            "state": self.state,
            "stats": {
                "messages_processed": self.stats.messages_processed,
                "messages_produced": self.stats.messages_produced,
                "errors": self.stats.errors,
                "last_processed": self.stats.last_processed,
                "last_error": self.stats.last_error,
            },
            "last_updated": time.time()
        }
        
        self.redis.set_json(f"agents:{self.agent_id}", agent_info)
        
        # Add to agent registry
        self.redis.client.sadd("agents:registry", self.agent_id)
    
    def announce(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Make a system-wide announcement.
        
        Args:
            message: The announcement message
            data: Optional data to include with the announcement
        """
        payload = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "message": message,
            "timestamp": time.time()
        }
        
        if data:
            payload["data"] = data
            
        self.pubsub.publish("system:announcements", payload)
    
    def _handle_announcement(self, announcement: Dict[str, Any]) -> None:
        """Handle system announcements.
        
        Override in subclasses to react to announcements.
        
        Args:
            announcement: The announcement data
        """
        pass
    
    def start(self) -> None:
        """Start the agent."""
        if self.running:
            return
            
        self.running = True
        self.state = AGENT_STATE_RUNNING
        self._update_agent_info()
        
        # Start pub/sub listener
        self.pubsub.run_in_thread()
        
        # Announce agent startup
        self.announce("Agent started")
    
    def stop(self) -> None:
        """Stop the agent."""
        if not self.running:
            return
            
        self.running = False
        self.state = AGENT_STATE_STOPPED
        self._update_agent_info()
        
        # Announce agent shutdown
        self.announce("Agent stopped")
        
        # Stop pub/sub listener
        self.pubsub.stop()


class ProducerAgent(BaseAgent):
    """Agent that produces tasks to be processed."""
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize the producer agent.
        
        Args:
            agent_id: Optional agent ID (generated if not provided)
        """
        super().__init__(
            agent_id=agent_id or f"producer-{uuid.uuid4().hex[:8]}",
            agent_type="producer"
        )
        
        # Initialize task stream
        self.task_stream = RedisStream("tasks")
        
        # Internal state
        self.producer_thread = None
        self.task_counter = 0
    
    def generate_task(self) -> Dict[str, Any]:
        """Generate a task for processing.
        
        Returns:
            A task dictionary
        """
        self.task_counter += 1
        task_id = f"task-{self.task_counter}"
        
        # Generate a random task type
        task_types = ["analysis", "processing", "aggregation", "validation"]
        task_type = random.choice(task_types)
        
        # Generate random task data
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "priority": random.randint(1, 10),
            "data": {
                "value": random.randint(1, 100),
                "text": f"Sample text for task {task_id}"
            },
            "created_at": time.time(),
            "producer_id": self.agent_id
        }
        
        return task
    
    def run_producer(self) -> None:
        """Run the producer loop."""
        while self.running:
            try:
                # Generate and publish a task
                task = self.generate_task()
                self.task_stream.add(task)
                
                # Update statistics
                self.stats.messages_produced += 1
                self.stats.last_processed = time.time()
                
                if self.stats.messages_produced % 10 == 0:
                    self.announce(
                        f"Produced {self.stats.messages_produced} tasks",
                        {"total_tasks": self.stats.messages_produced}
                    )
                
                # Update agent info in Redis
                self._update_agent_info()
                
                # Sleep for a bit
                time.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                self.stats.errors += 1
                self.stats.last_error = str(e)
                self.state = AGENT_STATE_ERROR
                self._update_agent_info()
                self.announce("Error in producer", {"error": str(e)})
                time.sleep(5)  # Wait before retrying
                self.state = AGENT_STATE_RUNNING
    
    def start(self) -> None:
        """Start the producer agent."""
        super().start()
        
        # Start producer thread
        self.producer_thread = threading.Thread(target=self.run_producer)
        self.producer_thread.daemon = True
        self.producer_thread.start()


class WorkerAgent(BaseAgent):
    """Agent that processes tasks from the stream."""
    
    def __init__(self, agent_id: Optional[str] = None, group_name: str = "workers"):
        """Initialize the worker agent.
        
        Args:
            agent_id: Optional agent ID (generated if not provided)
            group_name: Consumer group name
        """
        super().__init__(
            agent_id=agent_id or f"worker-{uuid.uuid4().hex[:8]}",
            agent_type="worker"
        )
        
        # Initialize task stream consumer
        self.task_stream = RedisStream("tasks")
        self.result_stream = RedisStream("results")
        self.group_name = group_name
        
        # Create consumer group if it doesn't exist
        try:
            self.task_stream.create_consumer_group(group_name, self.agent_id)
        except Exception:
            # Group might already exist
            pass
        
        # Internal state
        self.worker_thread = None
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return a result.
        
        Args:
            task: The task to process
            
        Returns:
            The processing result
        """
        # Simulate some processing time based on priority
        processing_time = max(0.1, 1.0 / task.get("priority", 1))
        time.sleep(processing_time)
        
        # Generate a result based on task type
        task_type = task.get("task_type", "unknown")
        task_data = task.get("data", {})
        
        if task_type == "analysis":
            result = {
                "analysis_score": task_data.get("value", 0) * 1.5,
                "analysis_result": "Completed analysis"
            }
        elif task_type == "processing":
            result = {
                "processed_value": task_data.get("value", 0) ** 2,
                "processing_result": "Processed successfully"
            }
        elif task_type == "aggregation":
            result = {
                "aggregated_value": sum(range(task_data.get("value", 0))),
                "aggregation_result": "Aggregated data"
            }
        else:
            result = {
                "validation_result": task_data.get("value", 0) > 50,
                "validation_message": "Validation complete"
            }
        
        # Combine with task info
        return {
            "task_id": task.get("task_id"),
            "task_type": task_type,
            "worker_id": self.agent_id,
            "result": result,
            "processing_time": processing_time,
            "completed_at": time.time()
        }
    
    def run_worker(self) -> None:
        """Run the worker loop."""
        while self.running:
            try:
                # Read tasks from the stream
                messages = self.task_stream.read_group(count=1, block=2000)
                
                if not messages:
                    continue
                
                for message in messages:
                    # Extract task and message ID
                    message_id = message["id"]
                    task = message["data"]
                    
                    # Process the task
                    result = self.process_task(task)
                    
                    # Publish the result
                    self.result_stream.add(result)
                    
                    # Acknowledge the message
                    self.task_stream.acknowledge(message_id)
                    
                    # Update statistics
                    self.stats.messages_processed += 1
                    self.stats.last_processed = time.time()
                    
                    # Update agent info
                    self._update_agent_info()
                    
                    if self.stats.messages_processed % 10 == 0:
                        self.announce(
                            f"Processed {self.stats.messages_processed} tasks",
                            {"total_processed": self.stats.messages_processed}
                        )
                    
            except Exception as e:
                self.stats.errors += 1
                self.stats.last_error = str(e)
                self.state = AGENT_STATE_ERROR
                self._update_agent_info()
                self.announce("Error in worker", {"error": str(e)})
                time.sleep(5)  # Wait before retrying
                self.state = AGENT_STATE_RUNNING
    
    def start(self) -> None:
        """Start the worker agent."""
        super().start()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self.run_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()


class MonitorAgent(BaseAgent):
    """Agent that monitors the system and reports statistics."""
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize the monitor agent.
        
        Args:
            agent_id: Optional agent ID (generated if not provided)
        """
        super().__init__(
            agent_id=agent_id or f"monitor-{uuid.uuid4().hex[:8]}",
            agent_type="monitor"
        )
        
        # Subscribe to result stream for monitoring
        self.result_stream = RedisStream("results")
        
        # Internal state
        self.monitor_thread = None
        self.task_types = {}
        self.worker_stats = {}
        self.report_interval = 5  # seconds
    
    def _handle_announcement(self, announcement: Dict[str, Any]) -> None:
        """Handle system announcements.
        
        Args:
            announcement: The announcement data
        """
        # Log the announcement
        agent_id = announcement.get("agent_id", "unknown")
        agent_type = announcement.get("agent_type", "unknown")
        message = announcement.get("message", "")
        
        print(f"ANNOUNCEMENT: [{agent_type}:{agent_id}] {message}")
    
    def process_results(self) -> None:
        """Process and analyze results."""
        try:
            # Read results from the stream
            messages = self.result_stream.read(count=10, block=2000)
            
            for message in messages:
                result = message["data"]
                
                # Extract information from the result
                task_type = result.get("task_type")
                worker_id = result.get("worker_id")
                
                # Update task type statistics
                if task_type not in self.task_types:
                    self.task_types[task_type] = 0
                self.task_types[task_type] += 1
                
                # Update worker statistics
                if worker_id not in self.worker_stats:
                    self.worker_stats[worker_id] = 0
                self.worker_stats[worker_id] += 1
                
                # Update monitor stats
                self.stats.messages_processed += 1
                self.stats.last_processed = time.time()
        except Exception as e:
            self.stats.errors += 1
            self.stats.last_error = str(e)
            print(f"Monitor error: {str(e)}")
    
    def generate_report(self) -> None:
        """Generate and publish a system report."""
        # Get all active agents
        agent_ids = self.redis.client.smembers("agents:registry")
        
        agents = {}
        for agent_id in agent_ids:
            if isinstance(agent_id, bytes):
                agent_id = agent_id.decode('utf-8')
                
            agent_data = self.redis.get_json(f"agents:{agent_id}")
            if agent_data:
                agents[agent_id] = agent_data
        
        # Compile report
        report = {
            "timestamp": time.time(),
            "agents": {
                "total": len(agents),
                "by_type": {},
                "by_state": {}
            },
            "tasks": {
                "by_type": self.task_types
            },
            "workers": {
                "performance": self.worker_stats
            }
        }
        
        # Count agents by type and state
        for agent_id, agent_data in agents.items():
            agent_type = agent_data.get("type", "unknown")
            agent_state = agent_data.get("state", "unknown")
            
            if agent_type not in report["agents"]["by_type"]:
                report["agents"]["by_type"][agent_type] = 0
            report["agents"]["by_type"][agent_type] += 1
            
            if agent_state not in report["agents"]["by_state"]:
                report["agents"]["by_state"][agent_state] = 0
            report["agents"]["by_state"][agent_state] += 1
        
        # Save report to Redis
        report_id = f"report:{int(time.time())}"
        self.redis.set_json(report_id, report)
        
        # Publish report
        self.announce("System report generated", {
            "report_id": report_id,
            "summary": {
                "agents": len(agents),
                "tasks_processed": sum(self.task_types.values())
            }
        })
        
        # Print report to console
        print("\n===== SYSTEM REPORT =====")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Agents: {len(agents)} total")
        for agent_type, count in report["agents"]["by_type"].items():
            print(f"  - {agent_type}: {count}")
        print("Task processing:")
        for task_type, count in self.task_types.items():
            print(f"  - {task_type}: {count}")
        print("Worker performance:")
        for worker_id, count in self.worker_stats.items():
            print(f"  - {worker_id}: {count} tasks")
        print("=========================\n")
    
    def run_monitor(self) -> None:
        """Run the monitor loop."""
        last_report_time = 0
        
        while self.running:
            try:
                # Process results
                self.process_results()
                
                # Generate periodic reports
                current_time = time.time()
                if current_time - last_report_time >= self.report_interval:
                    self.generate_report()
                    last_report_time = current_time
                
                # Update agent info
                self._update_agent_info()
                
            except Exception as e:
                self.stats.errors += 1
                self.stats.last_error = str(e)
                self.state = AGENT_STATE_ERROR
                self._update_agent_info()
                print(f"Monitor error: {str(e)}")
                time.sleep(5)  # Wait before retrying
                self.state = AGENT_STATE_RUNNING
    
    def start(self) -> None:
        """Start the monitor agent."""
        super().start()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self.run_monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()


def main():
    """Run the multi-agent system example."""
    print("Starting Redis-based Multi-Agent System Example")
    print("==============================================")
    
    # Initialize Redis client and clear previous data
    redis = RedisClient()
    
    # Clear previous data
    print("Clearing previous data...")
    for key in redis.client.keys("agents:*"):
        redis.client.delete(key)
    redis.client.delete("agents:registry")
    
    # Create agents
    print("Creating agents...")
    producer = ProducerAgent("producer-main")
    workers = [WorkerAgent(f"worker-{i}") for i in range(3)]
    monitor = MonitorAgent("monitor-main")
    
    # Start all agents
    print("Starting agents...")
    producer.start()
    for worker in workers:
        worker.start()
    monitor.start()
    
    try:
        # Run for a fixed duration
        print("System running, press Ctrl+C to stop...")
        duration = 60  # seconds
        time.sleep(duration)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    finally:
        # Stop all agents
        monitor.stop()
        for worker in workers:
            worker.stop()
        producer.stop()
    
    print("\nExample complete!")


if __name__ == "__main__":
    main()
