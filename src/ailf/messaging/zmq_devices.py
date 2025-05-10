"""ZeroMQ device patterns.

This module provides implementation of advanced ZeroMQ devices
for building robust distributed systems.
"""

# Import directly from the utils directory during development
# In a real package installation, we would copy the implementations here
try:
    from utils.zmq_devices import (
        ZMQDevice,
        ZMQForwarder,
        ZMQStreamer,
        ZMQProxy
    )
except ImportError:
    # Fallback implementations for when the package is installed as standalone
    import zmq
    import threading
    from typing import Optional, Tuple
    
    class ZMQDevice:
        """Base class for ZeroMQ device patterns.
        
        This implements the foundation for ZeroMQ device patterns that
        connect multiple sockets together to create routing topologies.
        """
        def __init__(self, context: Optional[zmq.Context] = None):
            """Initialize the device.
            
            Args:
                context: ZMQ context to use (creates one if None)
            """
            self.context = context or zmq.Context.instance()
            self._running = False
            self._thread = None
            
        def start(self) -> None:
            """Start the device in a background thread."""
            if self._running:
                return
                
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            
        def stop(self) -> None:
            """Stop the device."""
            self._running = False
            if self._thread:
                self._thread.join(timeout=1.0)
                
        def _run(self) -> None:
            """Run the device loop. Must be implemented by subclasses."""
            raise NotImplementedError("Subclasses must implement _run")
        
    class ZMQForwarder(ZMQDevice):
        """ZMQ Forwarder device (pub-sub).
        
        Connects a frontend SUB socket to a backend PUB socket,
        forwarding all messages received.
        """
        def __init__(self, frontend_addr: str, backend_addr: str, 
                    context: Optional[zmq.Context] = None):
            """Initialize the forwarder.
            
            Args:
                frontend_addr: Address for the frontend SUB socket
                backend_addr: Address for the backend PUB socket
                context: ZMQ context to use (creates one if None)
            """
            super().__init__(context)
            self.frontend_addr = frontend_addr
            self.backend_addr = backend_addr
            
        def _run(self) -> None:
            """Run the forwarder device."""
            try:
                # Basic implementation without full zmq.device capabilities
                frontend = self.context.socket(zmq.SUB)
                frontend.setsockopt(zmq.SUBSCRIBE, b"")
                frontend.bind(self.frontend_addr)
                
                backend = self.context.socket(zmq.PUB)
                backend.bind(self.backend_addr)
                
                while self._running:
                    try:
                        message = frontend.recv(zmq.NOBLOCK)
                        backend.send(message)
                    except zmq.Again:
                        # No message available, sleep briefly
                        import time
                        time.sleep(0.01)
            finally:
                frontend.close()
                backend.close()
        
    class ZMQStreamer(ZMQDevice):
        """ZMQ Streamer device (pipeline).
        
        Connects a frontend PULL socket to a backend PUSH socket,
        forwarding all messages received.
        """
        def __init__(self, frontend_addr: str, backend_addr: str,
                    context: Optional[zmq.Context] = None):
            """Initialize the streamer.
            
            Args:
                frontend_addr: Address for the frontend PULL socket
                backend_addr: Address for the backend PUSH socket
                context: ZMQ context to use (creates one if None)
            """
            super().__init__(context)
            self.frontend_addr = frontend_addr
            self.backend_addr = backend_addr
            
        def _run(self) -> None:
            """Run the streamer device."""
            try:
                frontend = self.context.socket(zmq.PULL)
                frontend.bind(self.frontend_addr)
                
                backend = self.context.socket(zmq.PUSH)
                backend.bind(self.backend_addr)
                
                while self._running:
                    try:
                        message = frontend.recv(zmq.NOBLOCK)
                        backend.send(message)
                    except zmq.Again:
                        # No message available, sleep briefly
                        import time
                        time.sleep(0.01)
            finally:
                frontend.close()
                backend.close()
        
    class ZMQProxy(ZMQDevice):
        """ZMQ Proxy device (router-dealer).
        
        Connects a frontend ROUTER socket to a backend DEALER socket,
        enabling request-reply message passing between clients and workers.
        """
        def __init__(self, frontend_addr: str, backend_addr: str,
                    context: Optional[zmq.Context] = None):
            """Initialize the proxy.
            
            Args:
                frontend_addr: Address for the frontend ROUTER socket
                backend_addr: Address for the backend DEALER socket
                context: ZMQ context to use (creates one if None)
            """
            super().__init__(context)
            self.frontend_addr = frontend_addr
            self.backend_addr = backend_addr
            
        def _run(self) -> None:
            """Run the proxy device."""
            try:
                frontend = self.context.socket(zmq.ROUTER)
                frontend.bind(self.frontend_addr)
                
                backend = self.context.socket(zmq.DEALER)
                backend.bind(self.backend_addr)
                
                # Use poll to avoid busy wait
                poller = zmq.Poller()
                poller.register(frontend, zmq.POLLIN)
                poller.register(backend, zmq.POLLIN)
                
                while self._running:
                    try:
                        socks = dict(poller.poll(timeout=100))
                        
                        if frontend in socks and socks[frontend] == zmq.POLLIN:
                            message = frontend.recv_multipart()
                            backend.send_multipart(message)
                            
                        if backend in socks and socks[backend] == zmq.POLLIN:
                            message = backend.recv_multipart()
                            frontend.send_multipart(message)
                    except zmq.ZMQError as e:
                        if e.errno == zmq.ETERM:
                            break  # Context terminated
            finally:
                frontend.close()
                backend.close()

__all__ = [
    "ZMQDevice",
    "ZMQForwarder",
    "ZMQStreamer",
    "ZMQProxy"
]
