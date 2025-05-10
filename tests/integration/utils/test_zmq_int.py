# Moved from utils/test_zmq.py

import zmq
import pytest

@pytest.fixture
def zmq_context():
    context = zmq.Context()
    yield context
    context.term()

def test_zmq_socket_creation(zmq_context):
    socket = zmq_context.socket(zmq.REQ)
    assert socket.type == zmq.REQ
    socket.close()

def test_zmq_socket_send_receive(zmq_context):
    sender = zmq_context.socket(zmq.PAIR)
    receiver = zmq_context.socket(zmq.PAIR)
    sender.bind("inproc://test")
    receiver.connect("inproc://test")

    sender.send(b"Hello")
    message = receiver.recv()
    assert message == b"Hello"

    sender.close()
    receiver.close()