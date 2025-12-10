
import pytest
from dap.client import DAPClient

def _wrap(body: bytes) -> bytes:
    return f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body

def test_partial_messages():
    """Test parsing logic when messages arrive in chunks."""
    client = DAPClient()
    
    body = b'{"seq": 1, "type": "event", "event": "stopped"}'
    msg = _wrap(body)
    
    # Split it
    part1 = msg[:20]
    part2 = msg[20:]
    
    # Feed part 1
    events = list(client.recv(part1))
    assert len(events) == 0
    
    # Feed part 2
    events = list(client.recv(part2))
    assert len(events) == 1
    assert events[0].event == "stopped"

def test_multiple_messages_in_one_chunk():
    """Test parsing multiple messages arriving in a single buffer."""
    client = DAPClient()
    
    body1 = b'{"seq": 1, "type": "event", "event": "stopped"}'
    body2 = b'{"seq": 2, "type": "event", "event": "initialized"}'
    
    msg = _wrap(body1) + _wrap(body2)
    
    # Feed both at once
    events = list(client.recv(msg))
    
    assert len(events) == 2
    assert events[0].event == "stopped"
    assert events[1].event == "initialized"

def test_extra_headers():
    """Test messages with extra headers like Content-Type are accepted."""
    client = DAPClient()
    
    content = b'{"seq": 1, "type": "event", "event": "stopped"}'
    # Manual construction ensuring length is correct
    msg = (
        f"Content-Length: {len(content)}\r\n"
        "Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n"
        "\r\n"
    ).encode("utf-8") + content
    
    events = list(client.recv(msg))
    assert len(events) == 1
    assert events[0].event == "stopped"

def test_utf8_encoding():
    """Test parsing utf-8 content with special characters."""
    client = DAPClient()
    
    body = '{"text": "héllo world 🐛"}'
    content = (
        f'{{"seq": 1, "type": "event", "event": "output", "body": {body}}}'
    ).encode("utf-8")
    
    msg = _wrap(content)
    
    events = list(client.recv(msg))
    assert len(events) == 1
    assert events[0].body["text"] == "héllo world 🐛"
