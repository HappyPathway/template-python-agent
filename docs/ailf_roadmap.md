# `ailf` Development Roadmap

This document outlines the development roadmap for the `ailf` (Agentic AI Library Framework), based on the planned enhancements detailed in the [Agent Components](./agent-components.md) documentation.

## I. Core Functional Pillars

### 1. Interaction Management (`ailf.interaction`)

-   [x] **Dedicated `ailf.interaction` Module:**
    -   [x] Introduce standardized Pydantic schemas in `ailf.schemas.interaction` for diverse message types (text, structured data, binary, multi-modal).
    -   [x] Develop `BaseInputAdapter` class to parse various input formats.
    -   [x] Develop `BaseOutputAdapter` class to format agent outputs.
    -   [x] Create `InteractionManager` to orchestrate adapters and manage interaction flow.

### 2. Memory Systems (`ailf.memory`)

-   [x] **Dedicated `ailf.memory` Module:**
    -   [x] In-memory storage implementation.
    -   [x] Redis-backed distributed cache implementation.
    -   [x] Implement `LongTermMemory` class:
        -   [x] Interfaces for file-based storage.
        -   [ ] Future integrations with vector databases.
    -   [x] Develop `ReflectionEngine` class:
        -   [x] Leverage `ailf.ai_engine.AIEngine` to analyze short-term memory content (e.g., `MemoryItem` schemas).
        -   [x] Extract insights (user preferences, key facts) and transfer to long-term storage (e.g., as `UserProfile`, `KnowledgeFact` schemas in `ailf.schemas.memory`).

### 3. Cognitive Processing & Reasoning (`ailf.cognition`)

-   [x] **New `ailf.cognition` Module (or enhanced `AIEngine`):**
    -   [x] Implement `ReActProcessor` to manage Reason-Act loop (using `ReActState` Pydantic schemas).
    -   [x] Implement `TaskPlanner` to decompose high-level goals into executable plans/steps (`Plan`, `PlanStep` schemas in `ailf.schemas.cognition`).
    -   [x] Implement `IntentRefiner` for advanced Chain-of-Thought and generating clarifying questions.
-   [x] **Advanced Prompt Engineering and Management:**
    -   [x] **Prompt Templating:**
        -   [x] Design `ailf.cognition` components to work with a structured library of versioned prompt templates.
        -   [x] Manage templates as configurable assets (files, DB entries) - Implemented `PromptLibrary` for file-based loading.
        -   [x] Define Pydantic schemas for prompt templates (e.g., `PromptTemplateV1`) including structure, placeholders, instructions, metadata.
    -   [x] **Prompt Versioning & Tracking:**
        -   [x] Implement versioning for prompt templates.
        -   [x] Log prompt template unique identifier/version in `LoggedInteraction` schema (via `InteractionLogger`).
        -   [ ] Enable `AdaptiveLearningManager` to interact with these templates for optimization.

### 4. Tool Integration & Utilization (`ailf.tooling`)

-   [x] **Enhanced `ToolDescription` Schemas (`ailf.schemas.tooling`):**
    -   [x] Include detailed metadata: input/output Pydantic schemas, categories, keywords, usage examples. (Status: Implemented in `ailf.schemas.tooling.ToolDescription`)
    -   [x] Add optional embeddings for semantic search and selection. (Status: Implemented in `ailf.schemas.tooling.ToolDescription`)
-   [ ] **`ToolSelector` Component (`ailf.tooling.selector`):**
    -   [x] Basic keyword-based selection implemented. (Status: Implemented in `ToolSelector`)
    -   [ ] Implement RAG-based tool selection using embeddings from `ToolDescription`.
    -   [ ] Integrate with `ToolRegistryClient` for fetching tool descriptions (dependency on Pillar 9).
-   [ ] **Consolidate and Refine `ToolManager` (`ailf.tooling.manager`):**
    -   [ ] Resolve duplication of `ToolManager` classes (current: `ailf.tooling.manager.ToolManager` and `ailf.tooling.execution.ToolManager`). The goal is to have a single, robust `ailf.tooling.manager.ToolManager`.
    -   [ ] Ensure `ToolManager` stores and utilizes the full `ToolDescription` for each registered tool.
    -   [ ] Implement auto-detection of async tool functions during registration if not specified in `ToolDescription`.
    -   [ ] Ensure secure and reliable execution of tools, including robust input/output validation using `input_schema_ref`/`output_schema_ref` from `ToolDescription`.
    -   [ ] Clarify relationship/integration with `AIEngine` if `AIEngine` is also intended to handle tool execution aspects.
-   [ ] **Enhanced Tool Execution (Responsibility of `ToolManager`):**
    -   [ ] `AIEngine` or a dedicated `ToolManager` to handle secure and reliable execution of selected tools. (Note: This is now primarily the role of the refined `ailf.tooling.manager.ToolManager`)

### 5. Agent Flow, Routing, and Task Delegation (`ailf.routing`)

-   [ ] **Dedicated `ailf.routing` Module:**
    -   [ ] Implement `TaskDelegator`:
        -   [ ] Send `DelegatedTaskMessage` (from `ailf.schemas.routing`) to other agents/workers.
        -   [ ] Track `TaskResultMessage` responses.
    -   [ ] Implement `AgentRouter`:
        -   [ ] Direct incoming requests (`StandardMessage` from `ailf.schemas.interaction`) to internal handlers or other agents.
        -   [ ] Base routing on predefined rules or LLM-driven `RouteDecision` (using `RouteDecisionContext` schema).
    -   [ ] Define standardized Pydantic schemas in `ailf.schemas.routing` for message formats.

### 6. Adaptive Learning via Feedback Loops (`ailf.feedback`)

-   [x] **Dedicated `ailf.feedback` Module:**
    -   [x] Implement `InteractionLogger`:
        -   [x] Structured logging of `LoggedInteraction` schemas (inputs, actions, outputs, user feedback, metrics, prompt IDs/versions).
        -   [x] Configurable backend for log storage.
    -   [ ] Implement `PerformanceAnalyzer`:
        -   [ ] Utilities/class to query and analyze structured logs.
        -   [ ] Derive metrics on prompt success by correlating outcomes with prompt versions.
        -   [ ] Identify correlations between prompt phrasing, parameters, and agent performance.
    -   [ ] **(Advanced) `AdaptiveLearningManager`:**
        -   [ ] Apply insights from `PerformanceAnalyzer` to modify agent behavior.
        -   [ ] Implement prompt self-correction and optimization using performance metrics.
        -   [ ] Facilitate A/B testing of prompt variations.
        -   [ ] Suggest or (with oversight) automatically apply modifications to prompt templates.
        -   [ ] Create a continuous feedback loop for prompt strategy refinement.

### 7. Inter-Agent Communication (ACP) (`ailf.communication`)

-   [ ] **Dedicated `ailf.communication` Module:**
    -   [x] Define and implement a formal Agent Communication Protocol (ACP) - Schemas defined in `ailf.schemas.acp`.
    -   [x] Create Pydantic models in `ailf.schemas.acp` for standardized ACP message types (e.g., `ACPMessageHeader`, `TaskRequestMessage`, `TaskResultMessage`, `KnowledgeQueryMessage`, `KnowledgeResponseMessage`, `InformationShareMessage`, `UserInterventionRequestMessage`, `UXNegotiationMessage`, `StatusUpdateMessage`, `ErrorMessage`, `AgentRegistrationMessage`, `AgentDeregistrationMessage`, `HeartbeatMessage`, `HeartbeatAckMessage`).
    -   [ ] Implement `ACPHandler` class:
        -   [ ] Utilize `ailf.messaging` components for sending/receiving ACP messages.
        -   [ ] Manage serialization/deserialization of structured ACP messages.

### 8. Remote Agent Communication

-   [ ] **Enhance `ailf.communication.ACPHandler` for Remote Communication:**
    -   [ ] Ensure durable message queuing (e.g., via Redis Streams).
    -   [ ] Robust handling for asynchronous tasks spanning network boundaries.
-   [x] **Enhance ACP Schemas for Remote Interactions:**
    -   [x] `UserInterventionRequestMessage` to support requesting user intervention.
    -   [x] New `UXNegotiationMessage` in `ailf.schemas.acp` for managing session resumption and negotiating UX capabilities.

### 9. Agent & Tool Registry Integration (Mesh Client-Side) (`ailf.registry_client`)

-   [ ] **New `ailf.registry_client` Module:**
    -   [ ] Provide client-side support for external agent/tool registries (e.g., `HttpRegistryClient`).
-   [x] **Expanded `ToolDescription` and `AgentDescription` Schemas:**
    -   [x] `ailf.schemas.tooling.ToolDescription`
    -   [x] New `ailf.schemas.agent.AgentDescription`
    -   [x] Support detailed ontologies, capability descriptions, I/O Pydantic schemas, communication endpoints, dependencies, historical performance metrics, cost information, embeddings.
-   [ ] **Integration with Cognitive Components:**
    -   [ ] `TaskPlanner` or `ToolSelector` (from `ailf.cognition` or `ailf.tooling`) to integrate with the registry client.
    -   [ ] Discover and fetch detailed descriptions of agents/tools from the mesh.

## II. Interoperability

### A. Agent2Agent (A2A) Protocol Integration

-   [ ] **A2A-Compliant Schemas:**
    -   [ ] Ensure `ailf.schemas.agent.AgentDescription` can serialize to A2A Agent Card JSON.
    -   [ ] Develop Pydantic models in `ailf.schemas.acp` (or new `ailf.schemas.a2a`) mapping to A2A Task, Message, Part.
-   [ ] **`ailf.communication.A2AClient`:**
    -   [ ] Develop a dedicated client for A2A HTTP interactions (fetching Agent Cards, sending tasks, managing responses, processing SSE).
-   [ ] **FastAPI Wrapper Base Classes for A2A Servers:**
    -   [ ] Provide base classes/utilities for FastAPI to simplify exposing `ailf` agents as A2A servers.
        -   [ ] Automate common A2A route setup.
        -   [ ] Serve `AgentDescription` as A2A Agent Card.
        -   [ ] Offer hooks for translating A2A requests to internal `ailf` messages and vice-versa.
        -   [ ] Assist in mapping `ailf` task states to A2A task states.
        -   [ ] Provide helpers for emitting A2A-compliant SSE based on `ailf` events.
        -   [ ] Facilitate A2A request context propagation.
-   [ ] **UX Negotiation Alignment:**
    -   [ ] Align `ailf`'s planned `UXNegotiationMessage` with A2A's dynamic UX negotiation concepts.
-   [ ] **Documentation and Examples:**
    -   [ ] Provide guides for building A2A-compliant `ailf` agents.

