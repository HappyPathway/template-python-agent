"""Unit tests for ACP schemas."""

import uuid
from datetime import datetime
import pytest
from pydantic import ValidationError, TypeAdapter

from ailf.schemas.acp import (
    ACPMessageHeader,
    ACPMessageType,
    AgentRegistrationPayload,
    AgentRegistrationMessage,
    AgentDeregistrationPayload,
    AgentDeregistrationMessage,
    HeartbeatPayload,
    HeartbeatMessage,
    HeartbeatAckPayload,
    HeartbeatAckMessage,
    AnyACPMessage,
    # Added other message types for completeness in tests if needed
    TaskRequestMessage, TaskRequestPayload,
    TaskResultMessage, TaskResultPayload,
    KnowledgeQueryMessage, KnowledgeQueryPayload,
    KnowledgeResponseMessage, KnowledgeResponsePayload,
    InformationShareMessage, InformationSharePayload,
    UserInterventionRequestMessage, UserInterventionRequestPayload,
    UXNegotiationMessage, UXNegotiationPayload,
    StatusUpdateMessage, StatusUpdatePayload,
    ErrorMessage, ErrorMessagePayload
)

def test_agent_registration_payload_valid():
    payload = AgentRegistrationPayload(
        agent_id="test_agent_001",
        agent_type="test_runner",
        capabilities=["run_tests", "report_results"],
        address="tcp://localhost:5555",
        metadata={"version": "1.0"}
    )
    assert payload.agent_id == "test_agent_001"
    assert payload.agent_type == "test_runner"
    assert payload.capabilities == ["run_tests", "report_results"]
    assert payload.address == "tcp://localhost:5555"
    assert payload.metadata == {"version": "1.0"}

def test_agent_registration_message_valid():
    header = ACPMessageHeader(
        sender_agent_id="registrar_001",
        message_type=ACPMessageType.AGENT_REGISTRATION
    )
    payload = AgentRegistrationPayload(
        agent_id="test_agent_002",
        agent_type="worker"
    )
    message = AgentRegistrationMessage(header=header, payload=payload)
    assert message.header.message_type == ACPMessageType.AGENT_REGISTRATION
    assert message.payload.agent_id == "test_agent_002"
    assert isinstance(message.header.message_id, uuid.UUID)
    assert isinstance(message.header.timestamp, datetime)

def test_agent_registration_payload_missing_required_fields():
    with pytest.raises(ValidationError):
        AgentRegistrationPayload(agent_type="test") # agent_id is missing
    with pytest.raises(ValidationError):
        AgentRegistrationPayload(agent_id="agent1") # agent_type is missing

def test_agent_deregistration_payload_valid():
    payload = AgentDeregistrationPayload(
        agent_id="test_agent_003",
        reason="shutdown"
    )
    assert payload.agent_id == "test_agent_003"
    assert payload.reason == "shutdown"

def test_agent_deregistration_message_valid():
    header = ACPMessageHeader(
        sender_agent_id="registrar_002",
        message_type=ACPMessageType.AGENT_DEREGISTRATION
    )
    payload = AgentDeregistrationPayload(agent_id="test_agent_004")
    message = AgentDeregistrationMessage(header=header, payload=payload)
    assert message.header.message_type == ACPMessageType.AGENT_DEREGISTRATION
    assert message.payload.agent_id == "test_agent_004"

def test_agent_deregistration_payload_missing_required_fields():
    with pytest.raises(ValidationError):
        AgentDeregistrationPayload() # agent_id is missing

def test_heartbeat_payload_valid():
    payload = HeartbeatPayload(
        agent_id="active_agent_001",
        load_indicator=0.75
    )
    assert payload.agent_id == "active_agent_001"
    assert payload.load_indicator == 0.75
    assert isinstance(payload.timestamp, datetime)

def test_heartbeat_message_valid():
    header = ACPMessageHeader(
        sender_agent_id="monitor_001",
        message_type=ACPMessageType.HEARTBEAT
    )
    payload = HeartbeatPayload(agent_id="active_agent_002")
    message = HeartbeatMessage(header=header, payload=payload)
    assert message.header.message_type == ACPMessageType.HEARTBEAT
    assert message.payload.agent_id == "active_agent_002"

def test_heartbeat_payload_missing_required_fields():
    with pytest.raises(ValidationError):
        HeartbeatPayload() # agent_id is missing

def test_heartbeat_ack_payload_valid():
    original_msg_id = uuid.uuid4()
    payload = HeartbeatAckPayload(
        original_message_id=original_msg_id,
        responder_agent_id="monitor_agent_002"
    )
    assert payload.original_message_id == original_msg_id
    assert payload.responder_agent_id == "monitor_agent_002"
    assert isinstance(payload.timestamp, datetime)

def test_heartbeat_ack_message_valid():
    original_msg_id = uuid.uuid4()
    header = ACPMessageHeader(
        sender_agent_id="active_agent_003",
        recipient_agent_id="monitor_003",
        message_type=ACPMessageType.HEARTBEAT_ACK
    )
    payload = HeartbeatAckPayload(
        original_message_id=original_msg_id,
        responder_agent_id="active_agent_003" # Should be the sender of ack
    )
    message = HeartbeatAckMessage(header=header, payload=payload)
    assert message.header.message_type == ACPMessageType.HEARTBEAT_ACK
    assert message.payload.original_message_id == original_msg_id
    assert message.payload.responder_agent_id == "active_agent_003"

def test_heartbeat_ack_payload_missing_required_fields():
    with pytest.raises(ValidationError):
        HeartbeatAckPayload(responder_agent_id="test") # original_message_id missing
    with pytest.raises(ValidationError):
        HeartbeatAckPayload(original_message_id=uuid.uuid4()) # responder_agent_id missing

def test_any_acp_message_union_type_registration():
    header = ACPMessageHeader(sender_agent_id="test_sender", message_type=ACPMessageType.AGENT_REGISTRATION)
    payload = AgentRegistrationPayload(agent_id="test_agent_reg", agent_type="type_a")
    message_data = {"header": header.model_dump(), "payload": payload.model_dump()}
    
    adapter = TypeAdapter(AnyACPMessage)
    parsed_message = adapter.validate_python(message_data)
    assert isinstance(parsed_message, AgentRegistrationMessage)
    assert parsed_message.payload.agent_id == "test_agent_reg"

def test_any_acp_message_union_type_heartbeat():
    header = ACPMessageHeader(sender_agent_id="test_sender_hb", message_type=ACPMessageType.HEARTBEAT)
    payload = HeartbeatPayload(agent_id="hb_agent_001")
    message_data = {"header": header.model_dump(), "payload": payload.model_dump()}
    
    adapter = TypeAdapter(AnyACPMessage)
    parsed_message = adapter.validate_python(message_data)
    assert isinstance(parsed_message, HeartbeatMessage)
    assert parsed_message.payload.agent_id == "hb_agent_001"

def test_any_acp_message_union_type_deregistration():
    header = ACPMessageHeader(sender_agent_id="test_sender_dereg", message_type=ACPMessageType.AGENT_DEREGISTRATION)
    payload = AgentDeregistrationPayload(agent_id="dereg_agent_001")
    message_data = {"header": header.model_dump(), "payload": payload.model_dump()}
    
    adapter = TypeAdapter(AnyACPMessage)
    parsed_message = adapter.validate_python(message_data)
    assert isinstance(parsed_message, AgentDeregistrationMessage)
    assert parsed_message.payload.agent_id == "dereg_agent_001"

def test_any_acp_message_union_type_heartbeat_ack():
    header = ACPMessageHeader(sender_agent_id="test_sender_hb_ack", message_type=ACPMessageType.HEARTBEAT_ACK)
    payload = HeartbeatAckPayload(original_message_id=uuid.uuid4(), responder_agent_id="hb_ack_responder_001")
    message_data = {"header": header.model_dump(), "payload": payload.model_dump()}
    
    adapter = TypeAdapter(AnyACPMessage)
    parsed_message = adapter.validate_python(message_data)
    assert isinstance(parsed_message, HeartbeatAckMessage)
    assert parsed_message.payload.responder_agent_id == "hb_ack_responder_001"

