#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import sys
import json  # noqa: F401  (used in debug logging and can be handy for future extensions)
import subprocess  # noqa: F401  (reserved for potential adapter process customization)
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dap.client import DAPClient, ClientState
from dap.events import (
    InitializedEvent,
    StoppedEvent,
    ContinuedEvent,
    ExitedEvent,
    TerminatedEvent,
    OutputEvent,
    ThreadEvent,
    ProcessEvent,
    ModuleEvent
)
from dap.structs import JSON
from dap_io import IO


class DAPEditor:
    """Main editor class with fixed DAP debugging support."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DAP Text Editor - Fixed Version")
        self.root.geometry("1400x900")
        
        # Editor state
        self.current_file = None
        self.dap_client = None
        self.io_handler = None
        self.is_debugging = False
        self.breakpoints = {}  # line_number -> breakpoint_info
        self.current_thread_id = None
        self.variables = {}  # variable_id -> variable_info
        self.stack_frames = []  # current call stack
        self.initialization_timeout = None
        self.session_started = False  # ensure we only launch/configure once per debug session
        
        # Event handling
        self.event_queue = queue.Queue()
        
        self.create_menu()
        self.create_toolbar()
        self.create_main_panel()
        self.create_status_bar()
        
        self.process_dap_events()
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Debug menu
        debug_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Debug", menu=debug_menu)
        debug_menu.add_command(label="Start Debugging", command=self.start_debugging, accelerator="F5")
        debug_menu.add_command(label="Stop Debugging", command=self.stop_debugging, accelerator="Shift+F5")
        debug_menu.add_separator()
        debug_menu.add_command(label="Continue", command=self.continue_execution, accelerator="F5")
        debug_menu.add_command(label="Step Over", command=self.step_over, accelerator="F10")
        debug_menu.add_command(label="Step Into", command=self.step_into, accelerator="F11")
        debug_menu.add_command(label="Step Out", command=self.step_out, accelerator="Shift+F11")
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_as_file())
        self.root.bind('<F5>', lambda e: self.start_debugging() if not self.is_debugging else self.continue_execution())
        self.root.bind('<Shift-F5>', lambda e: self.stop_debugging())
        self.root.bind('<F10>', lambda e: self.step_over())
        self.root.bind('<F11>', lambda e: self.step_into())
        self.root.bind('<Shift-F11>', lambda e: self.step_out())
        
    def create_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # File operations
        ttk.Button(toolbar, text="New", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Debug controls
        self.start_debug_btn = ttk.Button(toolbar, text="Start Debug", command=self.start_debugging)
        self.start_debug_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_debug_btn = ttk.Button(toolbar, text="Stop Debug", command=self.stop_debugging, state=tk.DISABLED)
        self.stop_debug_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Execution controls
        self.continue_btn = ttk.Button(toolbar, text="Continue", command=self.continue_execution, state=tk.DISABLED)
        self.continue_btn.pack(side=tk.LEFT, padx=2)
        
        self.step_over_btn = ttk.Button(toolbar, text="Step Over", command=self.step_over, state=tk.DISABLED)
        self.step_over_btn.pack(side=tk.LEFT, padx=2)
        
        self.step_into_btn = ttk.Button(toolbar, text="Step Into", command=self.step_into, state=tk.DISABLED)
        self.step_into_btn.pack(side=tk.LEFT, padx=2)
        
        self.step_out_btn = ttk.Button(toolbar, text="Step Out", command=self.step_out, state=tk.DISABLED)
        self.step_out_btn.pack(side=tk.LEFT, padx=2)
        
    def create_main_panel(self):
        # Create paned window
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Editor
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # Editor with line numbers and breakpoints
        editor_frame = ttk.Frame(left_frame)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Line numbers
        self.line_numbers = tk.Text(editor_frame, width=4, padx=3, pady=3, takefocus=0,
                                   border=0, background='lightgray', state=tk.DISABLED)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Breakpoint indicators
        self.breakpoint_canvas = tk.Canvas(editor_frame, width=20, bg='lightgray')
        self.breakpoint_canvas.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main editor
        self.editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE, undo=True, font=('Consolas', 10))
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind events
        self.editor.bind('<KeyRelease>', self.on_text_change)
        self.editor.bind('<Button-1>', self.on_click)
        self.editor.bind('<Control-Button-1>', self.toggle_breakpoint)
        
        # Bind breakpoint canvas clicks
        self.breakpoint_canvas.bind('<Button-1>', self.on_breakpoint_click)
        
        # Right panel - Debug info
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # Create notebook for debug panels
        self.debug_notebook = ttk.Notebook(right_frame)
        self.debug_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Variables tab
        self.create_variables_tab()
        
        # Call Stack tab
        self.create_call_stack_tab()
        
        # Breakpoints tab
        self.create_breakpoints_tab()
        
        # Output tab
        self.create_output_tab()
        
    def create_variables_tab(self):
        variables_frame = ttk.Frame(self.debug_notebook)
        self.debug_notebook.add(variables_frame, text="Variables")
        
        # Variables tree
        self.variables_tree = ttk.Treeview(variables_frame, columns=('value', 'type'), show='tree headings')
        self.variables_tree.heading('#0', text='Name')
        self.variables_tree.heading('value', text='Value')
        self.variables_tree.heading('type', text='Type')
        
        self.variables_tree.column('#0', width=150)
        self.variables_tree.column('value', width=100)
        self.variables_tree.column('type', width=80)
        
        # Scrollbar for variables
        variables_scroll = ttk.Scrollbar(variables_frame, orient=tk.VERTICAL, command=self.variables_tree.yview)
        self.variables_tree.configure(yscrollcommand=variables_scroll.set)
        
        self.variables_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        variables_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_call_stack_tab(self):
        stack_frame = ttk.Frame(self.debug_notebook)
        self.debug_notebook.add(stack_frame, text="Call Stack")
        
        # Call stack list
        self.stack_listbox = tk.Listbox(stack_frame)
        stack_scroll = ttk.Scrollbar(stack_frame, orient=tk.VERTICAL, command=self.stack_listbox.yview)
        self.stack_listbox.configure(yscrollcommand=stack_scroll.set)
        
        self.stack_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stack_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_breakpoints_tab(self):
        breakpoints_frame = ttk.Frame(self.debug_notebook)
        self.debug_notebook.add(breakpoints_frame, text="Breakpoints")
        
        # Breakpoints tree
        self.breakpoints_tree = ttk.Treeview(breakpoints_frame, columns=('line', 'status'), show='tree headings')
        self.breakpoints_tree.heading('#0', text='File')
        self.breakpoints_tree.heading('line', text='Line')
        self.breakpoints_tree.heading('status', text='Status')
        
        self.breakpoints_tree.column('#0', width=200)
        self.breakpoints_tree.column('line', width=50)
        self.breakpoints_tree.column('status', width=80)
        
        # Scrollbar for breakpoints
        breakpoints_scroll = ttk.Scrollbar(breakpoints_frame, orient=tk.VERTICAL, command=self.breakpoints_tree.yview)
        self.breakpoints_tree.configure(yscrollcommand=breakpoints_scroll.set)
        
        self.breakpoints_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        breakpoints_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_output_tab(self):
        output_frame = ttk.Frame(self.debug_notebook)
        self.debug_notebook.add(output_frame, text="Output")
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.debug_status_label = ttk.Label(self.status_bar, text="Not Debugging")
        self.debug_status_label.pack(side=tk.RIGHT, padx=5)
        
    def update_line_numbers(self):
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete(1.0, tk.END)
        
        line_count = int(self.editor.index('end-1c').split('.')[0])
        for i in range(1, line_count + 1):
            self.line_numbers.insert(tk.END, f"{i}\n")
            
        self.line_numbers.config(state=tk.DISABLED)
        
        # Update breakpoint indicators
        self.update_breakpoint_indicators()
        
    def update_breakpoint_indicators(self):
        self.breakpoint_canvas.delete("all")
        
        line_count = int(self.editor.index('end-1c').split('.')[0])
        line_height = 21  # approximate line height
        
        for line_num in self.breakpoints:
            if line_num <= line_count:
                y = (line_num - 1) * line_height + 10
                # Draw a red circle for breakpoint
                self.breakpoint_canvas.create_oval(5, y-5, 15, y+5, fill='red', outline='darkred')
        
    def on_text_change(self, event=None):
        self.update_line_numbers()
        
    def on_click(self, event=None):
        self.update_line_numbers()
        
    def on_breakpoint_click(self, event=None):
        if not self.current_file:
            return
            
        line_height = 20
        line_num = (event.y // line_height) + 1
        if line_num in self.breakpoints:
            self.remove_breakpoint(line_num)
        else:
            self.add_breakpoint(line_num)
        
    def toggle_breakpoint(self, event=None):
        if not self.current_file:
            return
            
        line = int(self.editor.index(tk.INSERT).split('.')[0])
        
        if line in self.breakpoints:
            self.remove_breakpoint(line)
        else:
            self.add_breakpoint(line)
            
    def add_breakpoint(self, line):
        self.breakpoints[line] = {"line": line, "verified": False}
        
        filename = os.path.basename(self.current_file) if self.current_file else "Unknown"
        self.breakpoints_tree.insert("", tk.END, text=filename, values=(line, "Pending"))
        self.update_breakpoint_indicators()
        
        # send updated breakpoints to the debug adapter if connected
        if self.dap_client and self.dap_client.is_initialized:
            self.sync_breakpoints()
            
    def remove_breakpoint(self, line):
        if line in self.breakpoints:
            del self.breakpoints[line]
            
            # Update UI
            for item in self.breakpoints_tree.get_children():
                if self.breakpoints_tree.item(item)["values"][0] == line:
                    self.breakpoints_tree.delete(item)
                    break
                    
            self.update_breakpoint_indicators()
                    
            # Send updated breakpoints to the debug adapter
            if self.dap_client and self.dap_client.is_initialized:
                self.sync_breakpoints()

    def sync_breakpoints(self):
        # Only send breakpoints if the adapter process is still running and
        # the DAP client has successfully initialized.
        if not (
            self.dap_client
            and self.dap_client.is_initialized
            and self.current_file
            and self.io_handler
            and self.io_handler.is_running()
        ):
            return
        
        if not self.breakpoints:
            # Nothing to sync
            return
        
        source = {"path": self.current_file}
        # DAP `setBreakpoints` replaces all breakpoints for a source,
        # so we must always send the full list.
        breakpoints = [{"line": line} for line in sorted(self.breakpoints.keys())]
        self.send_dap_request("setBreakpoints", {"source": source, "breakpoints": breakpoints})
                
    def new_file(self):
        self.current_file = None
        self.editor.delete(1.0, tk.END)
        self.update_line_numbers()
        self.status_label.config(text="New file")
        
    def open_file(self):
        filename = filedialog.askopenfilename(
            title="Open Python File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.delete(1.0, tk.END)
                self.editor.insert(1.0, content)
                self.current_file = filename
                self.update_line_numbers()
                self.status_label.config(text=f"Opened: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")
                
    def save_file(self):
        if self.current_file:
            try:
                content = self.editor.get(1.0, tk.END)
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_label.config(text=f"Saved: {os.path.basename(self.current_file)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
        else:
            self.save_as_file()
            
    def save_as_file(self):
        filename = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            try:
                content = self.editor.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.current_file = filename
                self.status_label.config(text=f"Saved: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
                
    def start_debugging(self):
        if not self.current_file:
            messagebox.showwarning("Warning", "Please open a file to debug")
            return
            
        self.save_file()
            
        self.session_started = False

        debug_adapter_cmd = f"{sys.executable} -m debugpy.adapter"
        
        try:
            self.log_output("Starting debug session...")
            self.log_output(f"Debug adapter command: {debug_adapter_cmd}")
            self.log_output(f"Working directory: {os.path.dirname(self.current_file)}")
            
            self.io_handler = IO(debug_adapter_cmd, os.path.dirname(self.current_file))
            
            # Note: debugpy requires `locale` to be a string if provided,
            # so we pass an explicit value here instead of leaving it as null.
            self.dap_client = DAPClient(
                clientID="dap-editor",
                clientName="DAP Text Editor",
                locale="en-US",
                pathFormat="path",
                supportsVariableType=True,
                supportsProgressReporting=True,
            )
            
            self.io_handler.start()
            
            time.sleep(0.5)
            
            init_data = self.dap_client.send()
            self.io_handler.write(init_data)
            self.log_output("Sent initialize request")
            
            time.sleep(0.5)
            
            threading.Thread(target=self.read_dap_responses, daemon=True).start()
            
            # Update UI
            self.start_debug_btn.config(state=tk.DISABLED)
            self.stop_debug_btn.config(state=tk.NORMAL)
            self.debug_status_label.config(text="Starting Debug Session...")
            
            # Set a timeout to check if initialization succeeds
            self.initialization_timeout = self.root.after(3000, self.check_debug_initialization)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start debugging: {e}")
            self.log_output(f"Error starting debug: {e}")
            self.reset_debug_ui()
            
    def check_debug_initialization(self):
        if self.dap_client and not self.dap_client.is_initialized:
            self.log_output("Warning: Debug initialization timeout")
            self.log_output("The debug adapter may not be responding properly")
            self.log_output("Try restarting the debug session")
            
    def reset_debug_ui(self):
        self.start_debug_btn.config(state=tk.NORMAL)
        self.stop_debug_btn.config(state=tk.DISABLED)
        self.continue_btn.config(state=tk.DISABLED)
        self.step_over_btn.config(state=tk.DISABLED)
        self.step_into_btn.config(state=tk.DISABLED)
        self.step_out_btn.config(state=tk.DISABLED)
        self.debug_status_label.config(text="Not Debugging")
            
    def stop_debugging(self):
        if self.dap_client and self.dap_client.is_initialized:
            self.send_dap_request("disconnect", {"restart": False})
            
        # Stop IO handler
        if self.io_handler:
            self.io_handler.stop()
            self.io_handler = None
            
        # Reset state
        self.dap_client = None
        self.is_debugging = False
        self.session_started = False
        self.current_thread_id = None
        self.variables = {}
        self.stack_frames = []
        
        # Update UI
        self.reset_debug_ui()
        
        # Clear debug panels
        self.variables_tree.delete(*self.variables_tree.get_children())
        self.stack_listbox.delete(0, tk.END)
        
        self.log_output("Debug session stopped")
        
    def continue_execution(self):
        if self.dap_client and self.dap_client.is_initialized:
            self.send_dap_request("continue", {"threadId": self.current_thread_id})
            self.debug_status_label.config(text="Running")
            
    def step_over(self):
        if self.dap_client and self.dap_client.is_initialized:
            self.send_dap_request("next", {"threadId": self.current_thread_id})
            
    def step_into(self):
        if self.dap_client and self.dap_client.is_initialized:
            self.send_dap_request("stepIn", {"threadId": self.current_thread_id})
            
    def step_out(self):
        if self.dap_client and self.dap_client.is_initialized:
            self.send_dap_request("stepOut", {"threadId": self.current_thread_id})
            
    def send_dap_request(self, method, params=None):
        if not (self.dap_client and self.io_handler):
            return
        
        params = params or {}
        try:
            # Map generic method names to the high-level DAPClient API.
            if method == "configurationDone":
                self.dap_client.configuration_done()
            elif method == "launch":
                # `launch` takes `program` plus any additional kwargs
                self.dap_client.launch(**params)
            elif method == "continue":
                self.dap_client.continue_execution(threadId=params["threadId"])
            elif method == "next":
                self.dap_client.next(threadId=params["threadId"])
            elif method == "stepIn":
                self.dap_client.step_in(threadId=params["threadId"])
            elif method == "stepOut":
                self.dap_client.step_out(threadId=params["threadId"])
            elif method == "stackTrace":
                self.dap_client.stack_trace(**params)
            elif method == "scopes":
                self.dap_client.scopes(**params)
            elif method == "setBreakpoints":
                self.dap_client.set_breakpoints(
                    source=params["source"],
                    breakpoints=params.get("breakpoints", []),
                )
            elif method == "variables":
                self.dap_client.variables(**params)
            elif method == "disconnect":
                # Ignore extra params like {"restart": False} for now.
                self.dap_client.disconnect()
            else:
                self.log_output(f"Unsupported DAP method: {method}")
                return

            # Flush any pending bytes from the client and write them to the adapter.
            request_data = self.dap_client.send()
            if request_data:
                self.io_handler.write(request_data)
            self.log_output(f"Sent: {method}")
        except Exception as e:
            self.log_output(f"Error sending {method}: {e}")
                
    def read_dap_responses(self):
        while self.io_handler and self.io_handler.alive:
            try:
                data = self.io_handler.read()
                if data:
                    self.log_output(f"Received {len(data)} bytes from debug adapter")
                    self.log_output(f"Raw data: {data.decode('utf-8', errors='ignore')[:200]}")
                    # Process DAP events (only if the client is still active)
                    if not self.dap_client:
                        break
                    events = list(self.dap_client.recv(data))
                    self.log_output(f"Parsed {len(events)} events")
                    for event in events:
                        self.event_queue.put(event)
                else:
                    # No data received, check if process is still alive
                    if not self.io_handler.is_running():
                        self.log_output("Debug adapter process terminated")
                        break
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                        
            except Exception as e:
                self.log_output(f"Error reading DAP responses: {e}")
                break
                
    def process_dap_events(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                self.handle_dap_event(event)
        except queue.Empty:
            pass
            
        # Schedule next check
        self.root.after(100, self.process_dap_events)
        
    def handle_dap_event(self, event):
        self.log_output(f"Received DAP event: {type(event).__name__}")
        self.log_output(f"Event details: {event}")
        
        # Many events come through as the generic Event type with an `event`
        # string and a `body` dict. For robustness we branch primarily on the
        # event name instead of the concrete Python class.
        event_kind = getattr(event, "event", None)
        body = getattr(event, "body", {}) or {}
        
        if event_kind == "initialized":
            # This covers both the synthetic InitializedEvent we emit after a
            # successful initialize response and any raw "initialized" events
            # coming from the adapter.
            # We MUST only react once; debugpy will error if we send multiple
            # launch/configurationDone sequences for the same session.
            if self.session_started:
                self.log_output("Ignoring duplicate 'initialized' event")
                return
            self.session_started = True
            self.log_output("Debug adapter initialized!")
            self.debug_status_label.config(text="Debug Session Active")
            self.is_debugging = True
            
            # Cancel timeout
            if self.initialization_timeout:
                self.root.after_cancel(self.initialization_timeout)
                self.initialization_timeout = None
            
            # Start debugging: launch then configurationDone. We use the
            # internal console and stop on entry so we can install user
            # breakpoints once the debug server is fully running.
            self.send_dap_request(
                "launch",
                {
                    "program": self.current_file,
                    "console": "internalConsole",
                    "stopOnEntry": True,
                },
            )
            self.send_dap_request("configurationDone")
            
        elif event_kind == "stopped":
            # Hit a breakpoint, step, or entry stop.
            self.debug_status_label.config(text="Stopped")
            self.continue_btn.config(state=tk.NORMAL)
            self.step_over_btn.config(state=tk.NORMAL)
            self.step_into_btn.config(state=tk.NORMAL)
            self.step_out_btn.config(state=tk.NORMAL)
            
            # Update thread ID
            thread_id = body.get("threadId")
            if thread_id is not None:
                self.current_thread_id = thread_id

            # Now that execution is stopped inside the debuggee, (re)send all
            # user breakpoints so they become active for subsequent execution.
            self.sync_breakpoints()
                
            # Request stack trace
            if self.current_thread_id:
                self.send_dap_request("stackTrace", {"threadId": self.current_thread_id})
            
        elif event_kind == "continued":
            self.debug_status_label.config(text="Running")
            self.continue_btn.config(state=tk.DISABLED)
            self.step_over_btn.config(state=tk.DISABLED)
            self.step_into_btn.config(state=tk.DISABLED)
            self.step_out_btn.config(state=tk.DISABLED)
            
        elif event_kind == "output":
            output_text = body.get("output", "")
            if output_text:
                self.log_output(f"Program output: {output_text}")
            
        elif event_kind == "exited":
            exit_code = body.get("exitCode")
            if exit_code is not None:
                self.log_output(f"Program exited with code: {exit_code}")
            else:
                self.log_output("Program exited")
            self.stop_debugging()
            
        elif event_kind == "response":
            # Handle responses to requests we sent
            command = body.get("command")
            if not body.get("success"):
                message = body.get("message", "Unknown error")
                self.log_output(f"Error in response to {command}: {message}")
                return

            response_body = body.get("body", {}) or {}
            
            if command == "stackTrace":
                stack_frames = response_body.get("stackFrames", [])
                self.stack_frames = stack_frames
                self.stack_listbox.delete(0, tk.END)
                for frame in stack_frames:
                    name = frame.get("name", "?")
                    line = frame.get("line", "?")
                    file_info = frame.get("source", {}).get("path", "?")
                    file_name = os.path.basename(file_info)
                    self.stack_listbox.insert(tk.END, f"{name} ({file_name}:{line})")
                
                # Automatically request scopes for the top stack frame
                if stack_frames:
                    top_frame_id = stack_frames[0].get("id")
                    if top_frame_id is not None:
                        self.send_dap_request("scopes", {"frameId": top_frame_id})
                    
            elif command == "scopes":
                scopes = response_body.get("scopes", [])
                if scopes:
                    # For simplicity, just get variables for the first scope (usually "Locals")
                    first_scope = scopes[0]
                    var_ref = first_scope.get("variablesReference")
                    if var_ref:
                        self.send_dap_request("variables", {"variablesReference": var_ref})
                        
            elif command == "variables":
                variables = response_body.get("variables", [])
                # Update variables tree
                # Clear existing items if this is a fresh update (naive implementation)
                # Ideally we would update specific nodes, but for this demo we just show the list.
                # Since we only request one scope's variables, clearing everything is "okay" for a simple view.
                self.variables_tree.delete(*self.variables_tree.get_children())
                for var in variables:
                    name = var.get("name", "?")
                    value = var.get("value", "?")
                    type_name = var.get("type", "")
                    self.variables_tree.insert("", tk.END, text=name, values=(value, type_name))
            
            elif command == "setBreakpoints":
                # Update breakpoint status
                breakpoints = response_body.get("breakpoints", [])
                # We need to map these back to our line numbers.
                # The response order matches the request order.
                # In sync_breakpoints, we sorted keys: existing_lines = sorted(self.breakpoints.keys())
                
                existing_lines = sorted(self.breakpoints.keys())
                for i, bp_resp in enumerate(breakpoints):
                    if i < len(existing_lines):
                        line = existing_lines[i]
                        verified = bp_resp.get("verified", False)
                        msg = "Verified" if verified else "Unverified"
                        
                        # Update internal state
                        if line in self.breakpoints:
                            self.breakpoints[line]["verified"] = verified
                        
                        # Update UI
                        for item in self.breakpoints_tree.get_children():
                            if self.breakpoints_tree.item(item)["values"][0] == line:
                                self.breakpoints_tree.item(item, values=(line, msg))
                                break
                        
                        # Redraw canvas indicator if verified
                        # (Optimally we could change color, but for now just ensured it stays)

        elif event_kind == "terminated":
            self.log_output("Debug session terminated")
            self.stop_debugging()
            
    def log_output(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"{message}\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        
    def run(self):
        self.root.mainloop()


def main():
    editor = DAPEditor()
    editor.run()


if __name__ == "__main__":
    main()
