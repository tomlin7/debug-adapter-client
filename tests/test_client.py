
import pytest
from dap.client import DAPClient, ClientState
from dap.events import InitializedEvent, StoppedEvent, TerminatedEvent
from dap.protocol import Response
import json

def _make_response_bytes(seq, request_seq, command, success=True, body=None):
    content = {
        "type": "response",
        "seq": seq,
        "request_seq": request_seq,
        "command": command,
        "success": success,
    }
    if body:
        content["body"] = body
    
    encoded = json.dumps(content).encode("utf-8")
    header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8")
    return header + encoded

def _make_event_bytes(seq, event_name, body=None):
    content = {
        "type": "event",
        "seq": seq,
        "event": event_name,
    }
    if body:
        content["body"] = body
        
    encoded = json.dumps(content).encode("utf-8")
    header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8")
    return header + encoded

def test_full_lifecycle():
    """Test a full debug session lifecycle."""
    client = DAPClient(clientID="test", clientName="Test")
    
    # 1. Initialize
    init_req_bytes = client.send()
    # Expect seq 0
    
    # Adapter responds to initialize (seq=0)
    response_bytes = _make_response_bytes(seq=1, request_seq=0, command="initialize", body={"supportsConfigurationDoneRequest": True})
    events = list(client.recv(response_bytes))
    
    assert len(events) == 1
    assert isinstance(events[0], InitializedEvent)
    
    # 2. Launch
    client.launch(program="main.py")
    client.send() # flush
    # Expect seq 1
    
    # Adapter responds to launch (seq=1)
    response_bytes = _make_response_bytes(seq=2, request_seq=1, command="launch")
    events = list(client.recv(response_bytes))
    
    print(f"Launch response event: {events[0]}")
    assert events[0].event == "response"
    assert events[0].body["command"] == "launch"
    
    # 3. Configuration Done
    client.configuration_done()
    client.send() # flush
    # Expect seq 2
    
    response_bytes = _make_response_bytes(seq=3, request_seq=2, command="configurationDone")
    list(client.recv(response_bytes))
    
    # 4. Breakpoint Hit
    stop_event_bytes = _make_event_bytes(seq=4, event_name="stopped", body={"reason": "breakpoint", "threadId": 1})
    events = list(client.recv(stop_event_bytes))
    assert events[0].event == "stopped"
    
    # 5. Continue
    client.continue_execution(threadId=1)
    client.send()
    # Expect seq 3
    
    response_bytes = _make_response_bytes(seq=5, request_seq=3, command="continue")
    list(client.recv(response_bytes))
    
    # 6. Disconnect
    client.disconnect()
    client.send()
    # Expect seq 4
    
    print(f"Unanswered requests before disconnect response: {client._unanswered_requests}")
    
    response_bytes = _make_response_bytes(seq=6, request_seq=4, command="disconnect")
    events = list(client.recv(response_bytes))
    
    print(f"Disconnect events: {events}")
    
    assert len(events) == 1
    assert isinstance(events[0], TerminatedEvent) or events[0].event == "terminated"

def test_unsolicited_events():
    """Test parsing events that come without a request."""
    client = DAPClient()
    client.send()
    
    out_evt_bytes = _make_event_bytes(seq=1, event_name="output", body={"category": "stdout", "output": "Hello World\n"})
    events = list(client.recv(out_evt_bytes))
    
    assert len(events) == 1
    assert events[0].event == "output"
    assert events[0].body["output"] == "Hello World\n"

def test_request_methods():
    """Test helper methods for sending requests."""
    client = DAPClient()
    client.send()
    client._state = ClientState.NORMAL
    
    client.next(threadId=1)
    req = client.send()
    assert b'"command": "next"' in req
    assert b'"threadId": 1' in req
