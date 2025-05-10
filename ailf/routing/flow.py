"""Components for task delegation and routing in ailf."""
from typing import Any, Callable, Dict, List, Optional, Awaitable
import asyncio

# Placeholder for AIEngine and messaging components
# from ailf.ai_engine import AIEngine
# from ailf.messaging import MessageBroker # or similar

from ailf.schemas.interaction import BaseMessage as StandardMessage
from ailf.schemas.routing import DelegatedTaskMessage, TaskResultMessage, RouteDecision, RouteDecisionContext

class TaskDelegator:
    """Handles sending delegated tasks and tracking their results."""

    def __init__(self, message_broker: Any, agent_id: str):
        """
        Initialize the TaskDelegator.

        :param message_broker: A component for sending/receiving messages (e.g., Redis pub/sub, ZMQ).
        :type message_broker: Any # Should be a specific message broker interface
        :param agent_id: The ID of the current agent, to be used as source_agent_id.
        :type agent_id: str
        """
        self.message_broker = message_broker
        self.agent_id = agent_id
        self._pending_tasks: Dict[str, asyncio.Future] = {}

    async def delegate_task(self, task_message: DelegatedTaskMessage) -> Any:
        """
        Send a DelegatedTaskMessage to another agent/worker and await its result.

        :param task_message: The task message to send.
        :type task_message: DelegatedTaskMessage
        :return: The result of the task execution.
        :rtype: Any
        :raises asyncio.TimeoutError: If the task does not complete within a timeout.
        :raises Exception: If the task execution results in an error reported by the worker.
        """
        if not task_message.source_agent_id:
            task_message.source_agent_id = self.agent_id
        
        future = asyncio.Future()
        self._pending_tasks[task_message.task_id] = future

        # In a real system, self.message_broker.publish would send the message.
        # The target agent would pick it up, process it, and send a TaskResultMessage back.
        # A listener (e.g., self.handle_task_result) would then resolve the future.
        print(f"TaskDelegator: Publishing task {task_message.task_id} to target {task_message.target_agent_id}")
        # await self.message_broker.publish(f"agent_tasks:{task_message.target_agent_id}", task_message.model_dump_json())
        
        try:
            # This timeout should be configurable
            result_message = await asyncio.wait_for(future, timeout=60.0) 
            if result_message.status == "failed":
                raise Exception(f"Task {result_message.task_id} failed: {result_message.error_message}")
            return result_message.result
        finally:
            del self._pending_tasks[task_message.task_id]

    def handle_task_result(self, result_message: TaskResultMessage) -> None:
        """
        Callback to handle incoming TaskResultMessages.
        This would typically be called by the message broker's subscription listener.

        :param result_message: The received task result message.
        :type result_message: TaskResultMessage
        """
        if result_message.task_id in self._pending_tasks:
            future = self._pending_tasks[result_message.task_id]
            if not future.done():
                future.set_result(result_message)
            else:
                # Future might have timed out already
                print(f"TaskDelegator: Received result for already resolved/timed-out task {result_message.task_id}")
        else:
            print(f"TaskDelegator: Received unexpected task result for {result_message.task_id}")

class AgentRouter:
    """Directs incoming requests to internal handlers or other agents."""

    def __init__(self, ai_engine: Optional[Any] = None, predefined_rules: Optional[Dict] = None):
        """
        Initialize the AgentRouter.

        :param ai_engine: Optional AI engine for LLM-driven routing decisions.
        :type ai_engine: Any # Should be ailf.ai_engine.AIEngine
        :param predefined_rules: Optional dictionary of predefined routing rules.
        :type predefined_rules: Optional[Dict]
        """
        self.ai_engine = ai_engine
        self.predefined_rules = predefined_rules or {}
        self._internal_handlers: Dict[str, Callable[[StandardMessage], Awaitable[Any]]] = {}

    def register_handler(self, handler_name: str, handler_func: Callable[[StandardMessage], Awaitable[Any]]) -> None:
        """
        Register an internal handler function.

        :param handler_name: Name of the handler.
        :type handler_name: str
        :param handler_func: Async callable that takes a StandardMessage and returns a response.
        :type handler_func: Callable[[StandardMessage], Awaitable[Any]]
        """
        self._internal_handlers[handler_name] = handler_func

    async def decide_route(self, message: StandardMessage, known_external_agents: Optional[List[Dict]] = None) -> RouteDecision:
        """
        Decide how to route an incoming message.
        Uses predefined rules first, then LLM if available and configured.

        :param message: The incoming StandardMessage.
        :type message: StandardMessage
        :param known_external_agents: Information about other known agents for delegation.
        :type known_external_agents: Optional[List[Dict]]
        :return: A RouteDecision object.
        :rtype: RouteDecision
        """
        # 1. Check predefined rules (simplified example)
        # Rules could be based on message.content_type, message.source, keywords in content, etc.
        if self.predefined_rules:
            for rule_pattern, target_handler_name in self.predefined_rules.items():
                # This is a very basic pattern match, real rules engine would be more complex
                if rule_pattern in message.content_type or (isinstance(message.content, dict) and rule_pattern in str(message.content.get("text", ""))):
                    if target_handler_name in self._internal_handlers:
                        return RouteDecision(target_handler=target_handler_name, reasoning="Matched predefined rule.")
                    # Could also target an external agent based on rules

        # 2. If no rule matched and AI engine is available, use LLM for decision
        if self.ai_engine:
            context = RouteDecisionContext(
                incoming_message=message,
                available_internal_handlers=list(self._internal_handlers.keys()),
                known_external_agents=known_external_agents or [],
                routing_rules=self.predefined_rules
            )
            # Placeholder for LLM call: 
            # llm_decision_json = await self.ai_engine.generate_structured_output(
            #    prompt=f"Based on the following context, decide how to route the message: {context.model_dump_json()}",
            #    output_schema=RouteDecision
            # )
            # return RouteDecision.model_validate(llm_decision_json)
            
            # Dummy LLM decision: if message contains "delegate", try to find a target agent
            if isinstance(message.content, dict) and "delegate" in str(message.content.get("text", "")).lower():
                if known_external_agents:
                    return RouteDecision(target_agent_id=known_external_agents[0]["id"], reasoning="LLM decided to delegate based on keyword.")
            # Fallback LLM decision: route to a default handler if available
            if "default_handler" in self._internal_handlers:
                 return RouteDecision(target_handler="default_handler", reasoning="LLM fallback to default handler.")

        # 3. Default fallback: if no decision, perhaps reject or route to a generic handler
        if "generic_handler" in self._internal_handlers:
            return RouteDecision(target_handler="generic_handler", reasoning="Default fallback to generic handler.")
        
        return RouteDecision(reasoning="No suitable route found.") # Indicates an issue or need for a catch-all

    async def route_message(self, message: StandardMessage, known_external_agents: Optional[List[Dict]] = None, delegator: Optional[TaskDelegator] = None) -> Any:
        """
        Decide on a route and then execute it (either call internal handler or delegate).

        :param message: The incoming message to route.
        :type message: StandardMessage
        :param known_external_agents: Information about other known agents.
        :type known_external_agents: Optional[List[Dict]]
        :param delegator: An instance of TaskDelegator, required if delegation might occur.
        :type delegator: Optional[TaskDelegator]
        :return: The result from the handler or delegated task.
        :rtype: Any
        :raises ValueError: If routing decision leads to delegation but no delegator is provided.
        """
        decision = await self.decide_route(message, known_external_agents)

        if decision.target_handler and decision.target_handler in self._internal_handlers:
            handler_func = self._internal_handlers[decision.target_handler]
            return await handler_func(message)
        elif decision.target_agent_id:
            if not delegator:
                raise ValueError("TaskDelegator is required for routing to an external agent.")
            
            # Construct a DelegatedTaskMessage from the StandardMessage
            # This is a simplification; mapping might be more complex
            delegated_task = DelegatedTaskMessage(
                task_id=f"task_{message.message_id}", # Ensure unique task_id
                target_agent_id=decision.target_agent_id,
                task_name=message.content_type, # Or derive from message content
                task_input=message.content.model_dump() if isinstance(message.content, BaseModel) else {"content": message.content},
                source_agent_id=delegator.agent_id
            )
            return await delegator.delegate_task(delegated_task)
        else:
            # No route found or decision was to reject/ignore
            print(f"AgentRouter: No action taken for message {message.message_id}. Reason: {decision.reasoning}")
            return None # Or raise an error, or return a specific "unhandled" response
