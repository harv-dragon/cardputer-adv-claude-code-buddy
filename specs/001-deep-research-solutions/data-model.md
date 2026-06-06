# Data Model: Cardputer-Adv Claude Code Buddy Firmware

**Feature**: 001-deep-research-solutions
**Created**: 2026-06-06

## Entity Definitions

### 1. AgentStatus

Represents the current state of the CLI agent running on the Mac host. Received via USB
CDC serial from the companion daemon and consumed by the display_ui module.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum | Yes | Message type: `status`, `permission`, `log`, `config` |
| `seq` | uint32 | Yes | Monotonic sequence number for dropped message detection |
| `state` | enum | Yes | Agent state: `idle`, `running`, `waiting_permission`, `error` |
| `agent` | string | No | Agent name: `claude-code`, `claude`, etc. Max 32 chars |
| `msg` | string | No | Human-readable status message. Max 128 chars |
| `tokens` | uint32 | No | Cumulative tokens consumed this session |
| `tokens_today` | uint32 | No | Tokens consumed today |
| `entries` | string[] | No | List of active command entries. Max 8 entries, each max 64 chars |
| `last_output` | string | No | Most recent terminal output line. Max 256 chars |
| `runtime_seconds` | uint32 | No | Agent session runtime in seconds |
| `permission_id` | string | No | Unique ID for the permission request (only for `permission` type) |
| `permission_hint` | string | No | Description of what needs approval (only for `permission` type) |
| `error_code` | uint16 | No | Error code (only for `error` state) |
| `error_message` | string | No | Error description (only for `error` state). Max 128 chars |

**Validation Rules**:
- `seq` MUST increment by 1 for each message. Gap > 1 = dropped message(s).
- `state` MUST be one of the 4 enumerated values.
- `type` = `permission` MUST include `permission_id` and `permission_hint`.
- `type` = `status` with `state` = `error` MUST include `error_message`.
- `entries` array MUST NOT exceed 8 elements.
- All strings are UTF-8 encoded, length limits are in bytes.

### 2. DeviceConfig

Persistent device configuration stored in NVS (Non-Volatile Storage).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `device_name` | string | `"Cardputer-Adv"` | USB device name (iProduct string) |
| `dictation_key` | uint8 | `0xE7` (Right GUI) | HID keycode for MacWhisper trigger |
| `dictation_modifier` | uint8 | `0x00` | HID modifier (0 = no modifier with Right GUI) |
| `brightness` | uint8 | `128` | Display backlight PWM (0-255) |
| `mic_gain` | float | `30.0` | ES8311 ADC PGA gain in dB (0-42) |
| `serial_baud` | uint32 | `115200` | CDC serial baud rate |
| `sleep_timeout` | uint16 | `300` | Idle seconds before screen dim (0 = never) |
| `audio_sample_rate` | uint32 | `16000` | UAC2 sample rate in Hz |

**Validation Rules**:
- `device_name`: Max 32 ASCII characters
- `dictation_key`: Valid HID usage ID (0x04-0xE7 range for keyboard keys)
- `brightness`: 0-255, PWM duty cycle
- `mic_gain`: 0.0-42.0 dB (ES8311 PGA range)
- `audio_sample_rate`: 8000, 16000, 22050, 44100, or 48000 Hz

### 3. DisplayMode

Represents the active display mode and rendering state. Internal to display_ui module.

| Field | Type | Description |
|-------|------|-------------|
| `current_mode` | enum | `agent_status`, `audio_input`, `idle` |
| `current_state` | enum | Agent state: `idle`, `running`, `waiting_permission`, `error` |
| `previous_mode` | enum | Previous display mode (for transition animation) |
| `mode_changed_at` | uint32 | FreeRTOS tick when mode last changed |
| `dirty_rects` | rect[] | List of screen regions needing redraw |
| `vu_level` | float | Current VU meter level in dBFS (-96 to 0) |
| `vu_peak` | float | Peak VU level in dBFS (decaying) |
| `frame_count` | uint32 | Frames rendered since mode switch |
| `last_frame_time` | uint32 | FreeRTOS tick of last frame render |
| `scroll_offset` | uint16 | Text scroll position for log output |

**State Transitions**:
```text
Mode transitions:
  idle → agent_status     (when agent session starts: state → running)
  idle → audio_input      (when mic capture begins, no agent)
  agent_status → idle     (when agent session ends: state → idle)
  agent_status → audio_input (when mic capture begins during agent session)
  audio_input → idle      (when mic capture stops)
  audio_input → agent_status (when agent session starts during recording)

State transitions (within agent_status mode):
  idle → running          (agent session starts)
  running → waiting_permission (permission request received)
  running → error         (agent error or host disconnect)
  waiting_permission → running (permission granted)
  waiting_permission → error   (permission denied)
  error → running         (agent recovers)
  any → idle              (agent session ends)
```

### 4. KeyEvent

Represents a physical key press/release on the Cardputer-Adv keyboard.

| Field | Type | Description |
|-------|------|-------------|
| `row` | uint8 | Keyboard matrix row (0-3) |
| `col` | uint8 | Keyboard matrix column (0-13) |
| `key_char` | char | ASCII character (if printable) |
| `state` | enum | `pressed`, `released`, `held` |
| `timestamp` | uint32 | FreeRTOS tick when event occurred |
| `hid_usage` | uint8 | Mapped HID usage code for USB report |
| `hid_modifier` | uint8 | HID modifier byte (Ctrl, Shift, Alt, GUI) |

**Key Mapping Rules**:
- Default mapping: Cardputer QWERTY keys → standard USB HID keyboard usage codes
- Special key: Cardputer `SPACE` (hold) → `Right GUI` (dictation trigger) + optional modifier
- Special key: Cardputer `Fn` + `key` → function key macros
- Key repeat: 30ms debounce, 500ms initial repeat delay, 30ms repeat rate

### 5. AudioBuffer

PCM audio ring buffer connecting I2S RX DMA to UAC2 TX callback.

| Field | Type | Description |
|-------|------|-------------|
| `buffer` | int16_t[1024] | Ring buffer array (1024 samples = 64ms at 16kHz) |
| `write_idx` | uint16 | DMA write position |
| `read_idx` | uint16 | UAC2 read position |
| `overflow_count` | uint32 | Number of buffer overflows detected |
| `underrun_count` | uint32 | Number of buffer underruns detected |
| `total_samples` | uint64 | Total samples captured since boot |

## Entity Relationships

```text
Mac Daemon                         Firmware
==========                         ========

AgentStatus ──(CDC Serial)──→ host_comm/protocol.cpp
                                  │
                                  ├──→ display_ui/ui_modes.cpp (DisplayMode)
                                  │
DeviceConfig ←──(NV Storage)── power_mgmt + usb_stack

KeyEvent ←──(I2C scan)────── keyboard/keymap.cpp
  │                               │
  └──→ HID Report ──(USB)──→ Mac (MacWhisper trigger)

AudioBuffer ←──(I2S DMA)──── audio_pipeline/i2s_capture.cpp
  │                               │
  └──→ UAC2 TX ────(USB)───→ Mac (system audio input)
```

## FreeRTOS Task Architecture

```text
Core 0 (Protocol Core):
  Task_UI          (priority 3, 4096 stack): Display rendering, mode switching
  Task_HostComm    (priority 2, 3072 stack): CDC serial RX/TX, JSON parsing
  Task_Keyboard    (priority 4, 2048 stack): I2C keyboard scan, debounce, HID dispatch

Core 1 (Audio Core):
  Task_Audio       (priority 5, 4096 stack): I2S RX DMA, ES8311 control, PCM buffering
  Task_USB         (priority 5, 3072 stack): TinyUSB device task, UAC2 callbacks
  Task_Power       (priority 1, 1536 stack): Battery ADC, sleep/wake monitoring
```

Task priorities: 0 (idle) to 5 (highest). Audio and USB share highest priority to avoid
buffer underruns. UI is lower priority — visual updates can be delayed without data loss.
