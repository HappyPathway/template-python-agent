"""Task Planner for AILF agents, decomposing goals into executable plans."""

import asyncio
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional, Type

from pydantic import BaseModel

from ailf.schemas.cognition import Plan, PlanStep

# Placeholder for AIEngine
# In a real scenario, this would be properly imported and configured.
try:
    from utils.ai.engine import AIEngine
except ImportError:
    class AIEngine: # type: ignore
        async def analyze(self, content: str, output_schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
            print(f"Warning: Using placeholder AIEngine. Analyze called for TaskPlanner with prompt: {system_prompt}")
            # Simulate AI generating a plan based on the goal
            if "setup a new project" in content.lower():
                steps = [
                    PlanStep(step_id=uuid.uuid4().hex, description="Define project requirements"),
                    PlanStep(step_id=uuid.uuid4().hex, description="Create project structure", dependencies=[steps[0].step_id if steps else ""]),
                    PlanStep(step_id=uuid.uuid4().hex, description="Install dependencies", dependencies=[steps[1].step_id if len(steps) > 1 else ""]),
                    PlanStep(step_id=uuid.uuid4().hex, description="Write initial code", dependencies=[steps[2].step_id if len(steps) > 2 else ""])
                ]
                return Plan(plan_id=uuid.uuid4().hex, goal=content, steps=steps)
            return Plan(plan_id=uuid.uuid4().hex, goal=content, steps=[PlanStep(step_id=uuid.uuid4().hex, description="Generated placeholder step")])

# Define a type for an async tool/step execution function
AsyncStepExecutor = Callable[[PlanStep, Dict[str, Any]], Coroutine[Any, Any, Any]]

class TaskPlanner:
    """
    Decomposes high-level goals into a sequence of executable steps (a Plan),
    and can orchestrate the execution of these plans.
    """

    def __init__(self, ai_engine: AIEngine):
        """
        Initializes the TaskPlanner.

        :param ai_engine: The AI engine for generating plans.
        :type ai_engine: AIEngine
        """
        self.ai_engine = ai_engine
        self.step_executors: Dict[str, AsyncStepExecutor] = {}
        # For more complex scenarios, a ToolRegistry might be used here
        # to find executors based on tool_name in PlanStep.

    def register_step_executor(self, step_type_or_tool_name: str, executor_func: AsyncStepExecutor) -> None:
        """
        Registers an asynchronous function to execute a specific type of plan step or tool.

        :param step_type_or_tool_name: An identifier for the step type or the specific tool name
                                       that this executor can handle (e.g., "code_generation", "file_io").
        :type step_type_or_tool_name: str
        :param executor_func: The asynchronous function that executes the step.
                              It should accept a PlanStep and a dictionary of context/results from dependent steps.
        :type executor_func: AsyncStepExecutor
        """
        self.step_executors[step_type_or_tool_name] = executor_func
        print(f"Step executor for '{step_type_or_tool_name}' registered.")

    async def generate_plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Plan:
        """
        Generates a plan to achieve a given goal using the AIEngine.

        :param goal: The high-level goal to achieve.
        :type goal: str
        :param context: Optional context to provide to the AIEngine for plan generation.
        :type context: Optional[Dict[str, Any]]
        :return: A Plan object detailing the steps to achieve the goal.
        :rtype: Plan
        """
        # Construct a prompt for the AIEngine to generate a plan.
        # This would be more sophisticated in a real system, possibly including available tools/capabilities.
        prompt_content = f"Goal: {goal}\n"
        if context:
            prompt_content += f"Context: {json.dumps(context)}\n"
        prompt_content += "Generate a step-by-step plan to achieve this goal. For each step, provide a description, any dependencies (step_ids), and optionally a suggested tool_name and tool_inputs."

        system_prompt = "You are a task planning assistant. Decompose the given goal into a sequence of actionable steps, outputting a Plan schema."
        
        plan_model = await self.ai_engine.analyze(
            content=prompt_content,
            output_schema=Plan,
            system_prompt=system_prompt
        )

        if not isinstance(plan_model, Plan):
            print("Error: AIEngine did not return a valid Plan. Returning a fallback plan.")
            # Fallback or error handling
            return Plan(plan_id=uuid.uuid4().hex, goal=goal, steps=[], current_status="failed_generation")
        
        plan_model.goal = goal # Ensure the original goal is set
        plan_model.plan_id = uuid.uuid4().hex # Ensure a unique plan ID
        return plan_model

    async def execute_plan(self, plan: Plan, initial_context: Optional[Dict[str, Any]] = None) -> Plan:
        """
        Executes a given plan step-by-step.

        This is a simplified executor. A more robust version would handle:
        - Parallel execution of independent steps.
        - More sophisticated error handling and retries.
        - Dynamic replanning if a step fails or new information arises.

        :param plan: The Plan object to execute.
        :type plan: Plan
        :param initial_context: Optional initial context for the plan execution.
        :type initial_context: Optional[Dict[str, Any]]
        :return: The Plan object with updated step statuses and results.
        :rtype: Plan
        """
        print(f"Executing plan '{plan.plan_id}' for goal: {plan.goal}")
        plan.current_status = "in_progress"
        
        # Store results of completed steps to pass to dependent steps
        completed_step_results: Dict[str, Any] = initial_context or {}
        
        # Simple topological sort based on dependencies (assumes no circular dependencies for now)
        # In a real system, a proper graph traversal (like Kahn's algorithm or DFS) would be used.
        execution_order: List[PlanStep] = []
        remaining_steps = list(plan.steps)
        
        # Iteratively add steps whose dependencies are met
        # This is a naive approach; a robust planner would use a graph library or proper algorithm
        while len(remaining_steps) > 0:
            added_in_pass = 0
            steps_to_remove_from_remaining = []
            for step in remaining_steps:
                if all(dep_id in completed_step_results for dep_id in step.dependencies):
                    execution_order.append(step)
                    steps_to_remove_from_remaining.append(step)
                    added_in_pass +=1
            
            for step_to_remove in steps_to_remove_from_remaining:
                remaining_steps.remove(step_to_remove)

            if added_in_pass == 0 and len(remaining_steps) > 0:
                print("Error: Could not resolve dependency order or circular dependency detected. Halting plan execution.")
                plan.current_status = "failed_dependency_resolution"
                # Mark remaining steps as failed or skipped
                for r_step in remaining_steps:
                    r_step.status = "skipped_dependency_issue"
                return plan

        for step in execution_order:
            if step.status == "completed": # Skip already completed steps if plan is re-executed
                continue

            print(f"  Executing step '{step.step_id}': {step.description}")
            step.status = "in_progress"
            plan.updated_at = __import__('time').time()

            # Gather inputs from dependencies
            dependency_inputs = {dep_id: completed_step_results.get(dep_id) for dep_id in step.dependencies}
            
            executor_key = step.tool_name or "default_executor" # Use tool_name or a generic type
            executor = self.step_executors.get(executor_key)

            if not executor:
                step.status = "failed_no_executor"
                step.result = f"No executor found for tool/type: {executor_key}"
                print(f"    Error: {step.result}")
                plan.current_status = "failed"
                # Optionally, halt entire plan or try to replan
                break 
            
            try:
                # Pass the step itself and results of its direct dependencies
                step_result = await executor(step, dependency_inputs)
                step.result = step_result
                step.status = "completed"
                completed_step_results[step.step_id] = step_result
                print(f"    Step '{step.step_id}' completed. Result: {str(step_result)[:100]}...")
            except Exception as e:
                step.status = "failed"
                step.result = f"Error during execution: {e}"
                print(f"    Error executing step '{step.step_id}': {e}")
                plan.current_status = "failed"
                # Optionally, halt entire plan or try to replan
                break # Halt on first failure for this simple executor
        
        if all(s.status == "completed" for s in plan.steps):
            plan.current_status = "completed"
        elif plan.current_status != "failed" and plan.current_status != "failed_dependency_resolution": # If not already failed
            # If some steps are not completed but no hard failure occurred during execution loop
            # (e.g. if loop exited due to other reasons, or if some steps were skipped)
            if any(s.status == "failed" or s.status == "failed_no_executor" or s.status == "skipped_dependency_issue" for s in plan.steps):
                 plan.current_status = "failed_partial_completion"
            else:
                 plan.current_status = "unknown_incomplete" # Should ideally not happen with current logic

        plan.updated_at = __import__('time').time()
        print(f"Plan execution finished. Final status: {plan.current_status}")
        return plan

# Example Usage (Illustrative)
async def example_task_planner_usage():
    # 1. Setup AIEngine (using placeholder)
    ai_engine_instance = AIEngine()

    # 2. Initialize TaskPlanner
    planner = TaskPlanner(ai_engine=ai_engine_instance)

    # 3. (Optional) Register step executors
    async def default_step_executor(step: PlanStep, dependencies_results: Dict[str, Any]) -> Any:
        """A generic executor that simulates work based on step description."""
        print(f"    DefaultExecutor: Running step '{step.description}' with dependency results: {dependencies_results}")
        await asyncio.sleep(0.1) # Simulate work
        return f"Successfully executed: {step.description}"

    planner.register_step_executor("default_executor", default_step_executor)
    # In a real system, you'd register executors for specific tools like "code_generator", "api_caller", etc.

    # 4. Generate a plan
    goal = "Setup a new Python project for web scraping, including installing requests and beautifulsoup4, and creating a main script."
    print(f"\n--- Generating Plan for Goal: {goal} ---")
    generated_plan = await planner.generate_plan(goal)
    
    if generated_plan and generated_plan.steps:
        print(f"Generated Plan '{generated_plan.plan_id}' with {len(generated_plan.steps)} steps:")
        for i, step in enumerate(generated_plan.steps):
            print(f"  {i+1}. {step.description} (ID: {step.step_id}, Deps: {step.dependencies})")
        
        # 5. Execute the plan
        print(f"\n--- Executing Plan '{generated_plan.plan_id}' ---")
        executed_plan = await planner.execute_plan(generated_plan)
        
        print(f"\n--- Plan Execution Summary for '{executed_plan.plan_id}' ---")
        print(f"Overall Plan Status: {executed_plan.current_status}")
        for step in executed_plan.steps:
            print(f"  Step '{step.step_id}': {step.description} - Status: {step.status}, Result: {str(step.result)[:100]}")
    else:
        print(f"Failed to generate a valid plan for the goal: {goal}")

if __name__ == "__main__":
    # asyncio.run(example_task_planner_usage()) # Commented out to prevent execution during tool use
    pass
