#!/usr/bin/env python3
"""
Simple DAP adapter mocking debugpy's API.

This creates a minimal DAP adapter that can communicate via stdin/stdout.
"""

import sys
import json
import threading
import time
from typing import Dict, Any

class SimpleDAPAdapter:
    def __init__(self):
        self.seq = 1
        self.running = True
        
    def send_message(self, message: Dict[str, Any]):
        """Send a DAP message."""
        message["seq"] = self.seq
        self.seq += 1
        
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        
        sys.stdout.write(header + content)
        sys.stdout.flush()
        
    def handle_initialize(self, args: Dict[str, Any]):
        """Handle initialize request."""
        print(f"[ADAPTER] Initialize request: {args}", file=sys.stderr)
        
        response = {
            "type": "response",
            "request_seq": args.get("seq", 1),
            "command": "initialize",
            "success": True,
            "body": {
                "supportsConfigurationDoneRequest": True,
                "supportsConditionalBreakpoints": True,
                "supportsHitConditionalBreakpoints": True,
                "supportsLogPoints": True,
                "supportsSetVariable": True,
                "supportsSetExpression": True,
                "supportsTerminateRequest": True,
                "supportsRestartRequest": True,
                "supportsCompletionsRequest": True,
                "supportsModulesRequest": True,
                "supportsReadMemoryRequest": True,
                "supportsWriteMemoryRequest": True,
                "supportsDisassembleRequest": True,
                "supportsCancelRequest": True,
                "supportsBreakpointLocationsRequest": True,
                "supportsLogPoints": True,
                "supportsDataBreakpoints": True,
                "supportsSetExpression": True,
                "supportsTerminateRequest": True,
                "supportsRestartRequest": True,
                "supportsCompletionsRequest": True,
                "supportsModulesRequest": True,
                "supportsReadMemoryRequest": True,
                "supportsWriteMemoryRequest": True,
                "supportsDisassembleRequest": True,
                "supportsCancelRequest": True,
                "supportsBreakpointLocationsRequest": True
            }
        }
        self.send_message(response)
        
        event = {
            "type": "event",
            "event": "initialized"
        }
        self.send_message(event)
        
    def handle_configuration_done(self, args: Dict[str, Any]):
        """Handle configurationDone request."""
        print(f"[ADAPTER] Configuration done request: {args}", file=sys.stderr)
        
        response = {
            "type": "response",
            "request_seq": args.get("seq", 1),
            "command": "configurationDone",
            "success": True
        }
        self.send_message(response)
        
    def handle_launch(self, args: Dict[str, Any]):
        """Handle launch request."""
        print(f"[ADAPTER] Launch request: {args}", file=sys.stderr)
        
        response = {
            "type": "response",
            "request_seq": args.get("seq", 1),
            "command": "launch",
            "success": True
        }
        self.send_message(response)
        
        time.sleep(1)
        event = {
            "type": "event",
            "event": "stopped",
            "body": {
                "reason": "breakpoint",
                "threadId": 1
            }
        }
        self.send_message(event)
        
    def run(self):
        """Main loop to handle DAP messages."""
        print("[ADAPTER] Simple DAP adapter started", file=sys.stderr)
        
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())
                    sys.stdin.readline()
                    content = sys.stdin.read(length)
                    
                    try:
                        message = json.loads(content)
                        print(f"[ADAPTER] Received message: {message}", file=sys.stderr)
                        
                        if message.get("type") == "request":
                            command = message.get("command")
                            args = message.get("arguments", {})
                            
                            if command == "initialize":
                                self.handle_initialize(message)
                            elif command == "configurationDone":
                                self.handle_configuration_done(message)
                            elif command == "launch":
                                self.handle_launch(message)
                            else:
                                print(f"[ADAPTER] Unknown command: {command}", file=sys.stderr)
                                
                    except json.JSONDecodeError as e:
                        print(f"[ADAPTER] JSON decode error: {e}", file=sys.stderr)
                        
            except Exception as e:
                print(f"[ADAPTER] Error: {e}", file=sys.stderr)
                break
                
        print("[ADAPTER] Simple DAP adapter stopped", file=sys.stderr)

if __name__ == "__main__":
    adapter = SimpleDAPAdapter()
    adapter.run()


