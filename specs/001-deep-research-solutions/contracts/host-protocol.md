# Host-to-Device Protocol Specification

**Feature**: 001-deep-research-solutions
**Contract Type**: Communication Protocol (CDC Serial)
**Version**: 1.0.0

## Overview

This protocol defines the communication between the Mac companion daemon (host) and the
Cardputer-Adv firmware (device) over USB CDC ACM serial at 115200 baud.

## Transport

- **Physical**: USB CDC ACM (Interface 3+4 in composite descriptor)
- **Framing**: Newline-delimited JSON (`\n` = 0x0A as frame delimiter)
- **Encoding**: UTF-8
- **Direction**: Host → Device (primary). Device → Host for acknowledgments (optional v2).
- **Maximum frame size**: 1024 bytes (including newline)
- **Flow control**: USB Bulk endpoint hardware flow control
- **Baud rate**: 115200 (logical; actual throughput is USB bulk endpoint speed)

## Message Schema

All messages are JSON objects with a `type` field determining the schema.

### Common Fields

```json
{
  "type": "<message_type>",
  "seq": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Message type: `status`, `permission`, `log`, `config` |
| `seq` | uint32 | Yes | Monotonic sequence number, wraps at 2^32. Used for dropped message detection |

### Type: `status` (Periodic Heartbeat)

Sent every ~500ms when an agent session is active. Provides current agent state and
statistics for the display.

```json
{
  "type": "status",
  "seq": 42,
  "state": "running",
  "agent": "claude-code",
  "msg": "Installing dependencies...",
  "tokens": 125000,
  "tokens_today": 42000,
  "entries": ["npm install", "tsc --build", "jest --coverage"],
  "last_output": "Tests passed: 42/42",
  "runtime_seconds": 1234
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"status"` |
| `seq` | uint32 | Yes | Sequence number |
| `state` | string | Yes | `"idle"`, `"running"`, `"waiting_permission"`, `"error"` |
| `agent` | string | No | Agent name, max 32 chars. Present when state ≠ idle |
| `msg` | string | No | Human-readable status, max 128 chars |
| `tokens` | uint32 | No | Cumulative session tokens. Present when state ≠ idle |
| `tokens_today` | uint32 | No | Tokens today. Present when state ≠ idle |
| `entries` | string[] | No | Active commands, max 8 entries × 64 chars each |
| `last_output` | string | No | Most recent output line, max 256 chars |
| `runtime_seconds` | uint32 | No | Session duration in seconds |

**State-Specific Field Requirements**:

| State | Required Fields | Optional Fields |
|-------|----------------|-----------------|
| `idle` | `type`, `seq`, `state` | None |
| `running` | `type`, `seq`, `state` | `agent`, `msg`, `tokens`, `tokens_today`, `entries`, `last_output`, `runtime_seconds` |
| `waiting_permission` | `type`, `seq`, `state`, `permission_id`, `permission_hint` | `agent` |
| `error` | `type`, `seq`, `state`, `error_message` | `agent`, `error_code` |

### Type: `permission` (Approval Request)

Sent when the agent issues a tool call requiring user approval.

```json
{
  "type": "permission",
  "seq": 43,
  "state": "waiting_permission",
  "permission_id": "req_abc123",
  "permission_hint": "run: rm -rf /tmp/build",
  "agent": "claude-code"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"permission"` |
| `seq` | uint32 | Yes | Sequence number |
| `state` | string | Yes | Must be `"waiting_permission"` |
| `permission_id` | string | Yes | Unique request ID, max 64 chars |
| `permission_hint` | string | Yes | What needs approval, max 128 chars |
| `agent` | string | No | Agent name |

**Device Behavior on Permission**:
- Display immediately switches to permission overlay (highest priority mode)
- Red border pulses on screen
- Physical SPACE key (held for 1s) = approve
- Physical ESC key = deny
- After 60s timeout with no response → auto-deny and return to previous mode

### Type: `log` (Terminal Output Line)

Sent for each new terminal output line from the agent.

```json
{
  "type": "log",
  "seq": 44,
  "state": "running",
  "output": "> jest --coverage",
  "timestamp": 1718143200
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"log"` |
| `seq` | uint32 | Yes | Sequence number |
| `state` | string | Yes | Current agent state |
| `output` | string | Yes | Output line, max 256 chars |
| `timestamp` | uint64 | No | Unix timestamp of output line |

### Type: `config` (Host → Device Settings)

Sent to configure device settings (brightness, mic gain, etc.). Persisted to NVS.

```json
{
  "type": "config",
  "seq": 45,
  "settings": {
    "brightness": 200,
    "mic_gain": 25.0
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"config"` |
| `seq` | uint32 | Yes | Sequence number |
| `settings` | object | Yes | Key-value map of settings to update. Keys match DeviceConfig entity fields |

## Error Handling

### Dropped Frame Detection

The device tracks the `seq` field. If `received_seq > expected_seq + 1`, one or more
frames were dropped. The device:
1. Increments a dropped frame counter (displayed in idle mode debug view)
2. If `state` changed in the missed frame(s), refreshes full display on next received frame
3. Continues processing with the new `seq` as the expected sequence

### Malformed JSON

If the JSON parser fails:
1. Skip the frame (discard until next `\n`)
2. Increment parse error counter
3. Display an error indicator (⚠) in the status bar for 3 seconds

### Host Disconnect

If no CDC serial data received for 5 seconds:
1. Set `state` to `error` with `error_message` = "Host disconnected"
2. Display error mode with "Disconnected" message
3. When data resumes, clear error and restore last known state

## Sequence Examples

### Agent Session Lifecycle

```text
Host → Device: {"type":"status","seq":1,"state":"idle"}
                     → Display: idle mode (clock, battery, connection)

Host → Device: {"type":"status","seq":2,"state":"running","agent":"claude-code",...}
                     → Display: agent_status mode, shows Claude Code info

Host → Device: {"type":"log","seq":3,"state":"running","output":"> npm install"}
                     → Display: adds "> npm install" to output area

Host → Device: {"type":"permission","seq":4,"state":"waiting_permission",
                "permission_id":"req_123","permission_hint":"run: rm -rf /tmp"}
                     → Display: permission overlay, pulsing red border
                     → User holds SPACE → approve

Host → Device: {"type":"status","seq":5,"state":"running","msg":"Building..."}
                     → Display: back to agent_status mode

Host → Device: {"type":"status","seq":6,"state":"idle"}
                     → Display: idle mode
```

## Host-Side Implementation Requirements

The Mac companion daemon MUST:
1. Detect and connect to the Cardputer-Adv CDC serial port (`/dev/tty.usbmodem*`)
2. Auto-reconnect if the serial port disappears and reappears
3. Send `status` heartbeat every 500ms when agent is active
4. Send `status` with `state: "idle"` every 5s when no agent is active
5. Include monotonically incrementing `seq` starting at 0
6. Keep each JSON frame under 1024 bytes (truncate `last_output` and `entries` if needed)
7. Buffer messages if the serial port is not ready; drop oldest if buffer exceeds 50 messages
