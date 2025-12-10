#!/usr/bin/env python3
import subprocess
import threading
import queue
import os
import time
from typing import Optional, Callable


class IO:
    """
    IO handler for communicating with debug adapter processes.
    
    This class manages the lifecycle of a debug adapter process and provides
    methods for reading from and writing to its stdin/stdout streams.
    """
    
    def __init__(self, command: str, working_directory: Optional[str] = None):
        """
        Initialize the IO handler.
        
        Args:
            command: Command to run the debug adapter
            working_directory: Working directory for the process
        """
        self.command = command
        self.working_directory = working_directory or os.getcwd()
        self.process: Optional[subprocess.Popen] = None
        self.alive = False
        
        # NOTE: We intentionally do NOT start a background read thread in the
        # main editor integration. The editor code (`DAPEditor.read_dap_responses`)
        # performs its own blocking reads on stdout. A background read loop here
        # would race with that logic and consume DAP messages before the editor
        # sees them, which breaks initialization.
        self.read_thread: Optional[threading.Thread] = None
        self.write_queue = queue.Queue()
        
        # Callbacks (used only by the standalone example at the bottom)
        self.on_output: Optional[Callable[[bytes], None]] = None
        self.on_error: Optional[Callable[[bytes], None]] = None
        
    def start(self):
        if self.alive:
            return
            
        try:
            # Parse command
            cmd_parts = self.command.split()
            self.process = subprocess.Popen(
                cmd_parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.working_directory,
                bufsize=0  # Unbuffered
            )
            
            self.alive = True
            
            # IMPORTANT:
            # Do NOT start the background read thread by default.
            # The DAP editor drives reads explicitly via `read()`; if we also
            # consumed stdout here, the editor would never see any bytes.
            # If you need async callbacks, you can re-enable this in a custom
            # usage, but keep it disabled for the editor integration.
            # self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            # self.read_thread.start()
            
            print(f"Started debug adapter: {self.command}")
            print(f"PID: {self.process.pid}")
            
        except Exception as e:
            print(f"Failed to start debug adapter: {e}")
            self.alive = False
            
    def stop(self):
        if not self.alive:
            return
            
        self.alive = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"Error stopping process: {e}")
                
        if self.read_thread:
            self.read_thread.join(timeout=1)
            
        print("Debug adapter stopped")
        
    def write(self, data: bytes):
        """Write data to the debug adapter's stdin."""
        if not self.alive or not self.process:
            print("[IO] Process not alive or not started, cannot write")
            return
            
        try:
            print(f"[IO] Writing {len(data)} bytes to stdin")
            print(f"[IO] Data: {data.decode('utf-8', errors='ignore')[:200]}")
            self.process.stdin.write(data)
            self.process.stdin.flush()
            print("[IO] Data written successfully")
        except Exception as e:
            print(f"[IO] Error writing to debug adapter: {e}")
            
    def read(self) -> bytes:
        """Read data from the debug adapter's stdout."""
        if not self.alive or not self.process:
            print("[IO] Process not alive or not started")
            return b""
            
        try:
            # Non-blocking read
            if self.process.stdout.readable():
                data = self.process.stdout.read(4096)
                if data:
                    print(f"[IO] Read {len(data)} bytes from stdout")
                    print(f"[IO] Raw data: {data.decode('utf-8', errors='ignore')[:200]}")
                return data if data else b""
        except Exception as e:
            print(f"[IO] Error reading from debug adapter: {e}")
            
        return b""
        
    def _read_loop(self):
        """Background thread for reading from stdout."""
        while self.alive and self.process:
            try:
                data = self.process.stdout.read(4096)
                if data:
                    if self.on_output:
                        self.on_output(data)
                else:
                    time.sleep(0.01)  # Small delay to prevent busy waiting
            except Exception as e:
                print(f"Error in read loop: {e}")
                break
                
    def is_running(self) -> bool:
        if not self.process:
            return False
            
        return self.process.poll() is None
        
    def get_exit_code(self) -> Optional[int]:
        if not self.process:
            return None
            
        return self.process.returncode


# Example usage
if __name__ == "__main__":
    # Test with a simple command
    io = IO("python -c 'print(\"Hello from debug adapter\")'")
    
    def on_output(data):
        print(f"Received: {data.decode()}")
        
    io.on_output = on_output
    io.start()
    
    time.sleep(2)
    
    io.stop()
