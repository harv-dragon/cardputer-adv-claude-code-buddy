#!/usr/bin/env python3
"""
Test Sender — Claude Code Buddy Mock Agent Status Generator

Sends JSON protocol frames over USB CDC serial to the Cardputer-Adv
for testing the display UI and protocol parser without a real Claude Code agent.

Usage:
    python tools/test_sender.py                          # Auto-detect port
    python tools/test_sender.py --port /dev/tty.usbmodem* # Explicit port
    python tools/test_sender.py --mock                    # Print to stdout only

Protocol: contracts/host-protocol.md
"""

import argparse
import json
import random
import sys
import time
import os

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# ─── Agent State Simulation ────────────────────────────────────

STATES = ["idle", "running", "waiting_permission", "error"]
SAMPLE_COMMANDS = [
    ["npm install"],
    ["npm install", "tsc --build"],
    ["npm install", "tsc --build", "jest --coverage"],
    ["git pull origin main", "pip install -r requirements.txt"],
    ["cargo build --release"],
    ["docker compose up -d"],
]
SAMPLE_OUTPUTS = [
    "added 142 packages in 3.2s",
    "src/index.ts:42:5 - error TS2322: Type 'string' is not assignable to type 'number'",
    "Tests: 42 passed, 0 failed, 0 skipped",
    "Already up to date.",
    "Successfully installed requests-2.31.0",
    "Compiling my_app v0.1.0",
]

class MockAgent:
    """Simulates a Claude Code agent session cycling through states."""

    def __init__(self):
        self.seq = 0
        self.state = "idle"
        self.tokens = 0
        self.tokens_today = 0
        self.runtime = 0
        self.entries = []
        self.last_output = ""
        self.state_timer = 0.0
        self.state_duration = 0.0

    def next_message(self, dt: float) -> dict | None:
        """Generate the next status message. Returns None if no change."""
        self.runtime += dt
        self.state_timer += dt

        # State transitions (simulated agent lifecycle)
        if self.state == "idle" and self.state_timer > 5.0:
            self._transition("running")

        elif self.state == "running" and self.state_timer > 8.0:
            # Randomly go to permission or continue running
            if random.random() < 0.3:
                self._transition("waiting_permission")
            else:
                self._new_output()

        elif self.state == "waiting_permission" and self.state_timer > 3.0:
            # Auto-approve after 3 seconds (simulates user pressing SPACE)
            self._transition("running")

        elif self.state == "error" and self.state_timer > 4.0:
            self._transition("idle")

        elif self.state == "running":
            # Periodic output while running
            if self.state_timer > 2.0 and random.random() < 0.5:
                self._new_output()

        # Token accumulation while running
        if self.state in ("running", "waiting_permission"):
            self.tokens += int(dt * 250)  # ~250 tokens/sec
            self.tokens_today = self.tokens

        return self._build_message()

    def _transition(self, new_state: str):
        self.state = new_state
        self.state_timer = 0.0
        if new_state == "running":
            self.entries = random.choice(SAMPLE_COMMANDS)
        elif new_state == "error":
            self.last_output = "Error: Connection timeout"

    def _new_output(self):
        self.state_timer = 0.0
        self.last_output = random.choice(SAMPLE_OUTPUTS)

    def _build_message(self) -> dict:
        self.seq += 1
        msg = {
            "type": "status" if self.state != "waiting_permission" else "permission",
            "seq": self.seq,
            "state": self.state,
        }

        if self.state != "idle":
            msg["agent"] = "claude-code"
            msg["tokens"] = self.tokens
            msg["tokens_today"] = self.tokens_today
            msg["runtime_seconds"] = int(self.runtime)

        if self.state == "running":
            msg["msg"] = f"Working... ({self.entries[0] if self.entries else 'processing'})"
            msg["entries"] = self.entries
            msg["last_output"] = self.last_output

        if self.state == "waiting_permission":
            msg["msg"] = "Approval required"
            msg["permission_id"] = f"req_{random.randint(1000, 9999)}"
            msg["permission_hint"] = random.choice([
                "run: rm -rf /tmp/build",
                "run: npm publish --access public",
                "write: /etc/hosts (requires sudo)",
                "POST https://api.example.com/deploy",
            ])
            msg["last_output"] = self.last_output

        if self.state == "error":
            msg["error_message"] = self.last_output
            msg["error_code"] = 500

        return msg


# ─── Serial Port Finder ────────────────────────────────────────

def find_cardputer_port() -> str | None:
    """Find the Cardputer-Adv CDC serial port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # CDC ACM devices often have USB VID:PID 0x303A:0x4001
        if port.vid == 0x303A and port.pid == 0x4001:
            return port.device
        # Fallback: match by name
        if "usbmodem" in port.device.lower():
            return port.device
    return None


# ─── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cardputer-Adv CCB Test Sender")
    parser.add_argument("--port", help="Serial port (e.g., /dev/tty.usbmodem*)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--mock", action="store_true", help="Print to stdout only (no serial)")
    parser.add_argument("--rate", type=float, default=0.5, help="Message interval in seconds")
    parser.add_argument("--burst", type=int, default=0, help="Send N messages as fast as possible (reliability test)")
    parser.add_argument("--list", action="store_true", help="List available serial ports and exit")
    args = parser.parse_args()

    if args.list:
        print("Available serial ports:")
        for port in serial.tools.list_ports.comports():
            print(f"  {port.device} — {port.description} (VID:{port.vid:04X} PID:{port.pid:04X})")
        return

    # Open serial or mock
    ser = None
    if args.mock:
        print("[MOCK MODE] Printing JSON to stdout\n")
    else:
        port = args.port or find_cardputer_port()
        if not port:
            print("ERROR: Cardputer-Adv CDC serial port not found.")
            print("Is the device connected? Try --list to see available ports.")
            print("Or use --mock to test without hardware.")
            sys.exit(1)

        print(f"Connecting to {port} at {args.baud} baud...")
        ser = serial.Serial(port, args.baud, timeout=1)
        print(f"Connected! Sending messages every {args.rate}s\n")

    agent = MockAgent()
    start_time = time.time()
    sent_count = 0
    burst_count = args.burst

    try:
        while True:
            dt = time.time() - start_time
            start_time = time.time()

            msg = agent.next_message(0.5 if burst_count > 0 else dt)

            if msg:
                json_str = json.dumps(msg)
                if ser:
                    ser.write(json_str.encode() + b"\n")
                    ser.flush()
                else:
                    print(json_str)
                sent_count += 1

                if burst_count > 0:
                    burst_count -= 1
                    if burst_count == 0:
                        print(f"\nBurst complete: {sent_count} messages sent")
                    # No delay during burst

            if burst_count == 0:
                time.sleep(args.rate)

    except KeyboardInterrupt:
        print(f"\n\nStopped. Sent {sent_count} messages.")
        if ser:
            ser.close()


if __name__ == "__main__":
    main()
