# Technical Research: Cardputer-Adv Claude Code Buddy Firmware

**Feature**: 001-deep-research-solutions
**Created**: 2026-06-06
**Status**: Phase 0 Complete

## Research Topics

### 1. TinyUSB UAC2 Microphone on ESP32-S3 (Arduino Framework)

**Decision**: Use Espressif's TinyUSB fork with `CFG_TUD_AUDIO=1` enabled, configured as
a USB composite device with 3 interfaces: UAC2 Audio Input (microphone), HID Keyboard,
and CDC ACM (serial). Build on the UniGeek PlatformIO + Arduino base.

**Rationale**:
- Arduino-ESP32 core (v3.x) does NOT enable `CFG_TUD_AUDIO` in its default TinyUSB build
  (confirmed via Espressif issue #12053). UAC2 must be enabled at the SDK level.
- UniGeek currently uses Arduino's built-in USB HID — which uses the Arduino USB stack,
  NOT TinyUSB directly. To add UAC2, we must switch UniGeek from `ARDUINO_USB_MODE=1`
  (hardware CDC) to TinyUSB mode with custom descriptors.
- The `esp-iot-solution` repository has a working UAC2 device driver (`esp_device_uac`)
  but it is ESP-IDF only. The UAC2 descriptor patterns from this component are directly
  portable to our TinyUSB configuration.
- **atomic14/esp32-usb-uac-experiments** has the cleanest working example of ESP32-S3
  TinyUSB UAC2 microphone. Key patterns to copy:
  - UAC2 alternate interface descriptor (Alt 0: no streaming, Alt 1: streaming enabled)
  - `tud_audio_tx_done_pre_load_cb()` callback for feeding PCM data to USB
  - ISOCHRONOUS endpoint configuration (EP IN, adaptive, 1ms interval)
  - Clock source descriptor (internal clock, 16kHz)

**Alternatives Considered**:
- **Pure Arduino USB stack**: Rejected — UAC2 not supported (Espressif issue #12053, open since 2024)
- **ESP-IDF directly**: Viable but would lose M5Cardputer library and TFT_eSPI. Hybrid
  Arduino-as-component within ESP-IDF is the preferred v2 approach but adds complexity.
- **chegewara/EspTinyUSB**: Powerful but single-maintainer risk. UAC2 support is partial.

**Implementation Notes**:
- Switch `platformio.ini` from `ARDUINO_USB_MODE=1` to TinyUSB mode:
  ```ini
  build_flags =
      -DARDUINO_USB_MODE=0
      -DUSE_TINYUSB=1
      -DCFG_TUD_AUDIO=1
      -DCFG_TUD_AUDIO_FUNC_1_N_BYTES_SAMPLE=2
      -DCFG_TUD_AUDIO_FUNC_1_SAMPLE_RATE=16000
  ```
- USB composite descriptor layout (3 interfaces):
  ```text
  Interface 0: UAC2 Audio Control (Standard)
    Alt 0: No streaming
    Alt 1: Streaming interface (ISOCHRONOUS IN endpoint, 16-bit 16kHz mono)
  Interface 1: HID Keyboard (Boot Protocol)
    IN endpoint (8-byte reports, 1ms polling)
  Interface 2: CDC ACM (Virtual Serial Port)
    Bulk IN + Bulk OUT endpoints
  ```
- UAC2 clock source: Internal oscillator, 16kHz ± 0.1% (USB Full-Speed tolerance)

**References**:
- atomic14/esp32-usb-uac-experiments: `main/usb_descriptors.c`
- espressif/arduino-esp32 issue #12053: UAC2 discussion and API proposals
- TinyUSB upstream: `examples/device/audio/` for UAC2 descriptor patterns
- USB-IF Audio Device Class Specification 2.0

---

### 2. ES8311 Microphone Capture Path on Cardputer-Adv

**Decision**: Configure ES8311 ADC path via `esp_codec_dev` component for
initialization, then use direct I2S RX DMA for the data transfer from the ES8311's
ASDOUT pin (GPIO46) to a PCM ring buffer. The M5Cardputer.Speaker API is speaker-only;
mic capture requires bypassing it.

**Rationale**:
- The M5Cardputer library wraps ES8311 for **speaker output only** (confirmed via
  source analysis and community reports). The `M5Cardputer.Speaker.playRaw()` API
  writes PCM data TO the codec but has no read path.
- ES8311 has separate ADC and DAC signal chains. The ADC output is on the ASDOUT pin
  (GPIO46 on Cardputer-Adv) via I2S. We need to configure I2S in RX (receive) mode
  on the ESP32-S3 to capture this.
- The `esp_codec_dev` component provides `esp_codec_dev_read()` for ADC capture, but
  using it within an Arduino project requires the component to be included as an
  ESP-IDF dependency.
- Cardputer-Adv pin mapping for audio:
  ```text
  ES8311 SDA  → GPIO8  (I2C data)
  ES8311 SCL  → GPIO9  (I2C clock)
  ES8311 SCLK → GPIO41 (I2S bit clock)
  ES8311 ASDOUT → GPIO46 (I2S ADC serial data output) ← THIS is our capture pin
  ES8311 LRCK → GPIO43 (I2S word select / left-right clock)
  ES8311 DSDIN → GPIO42 (I2S DAC serial data input — speaker path)
  ```

**I2S RX Configuration**:
```c
// I2S channel in RX mode for mic capture
i2s_chan_config_t rx_chan_cfg = {
    .id = I2S_NUM_1,
    .role = I2S_ROLE_MASTER,
    .dma_desc_num = 4,
    .dma_frame_num = 256,
    .auto_clear = true,
};
i2s_new_channel(&rx_chan_cfg, NULL, &rx_handle);

i2s_std_config_t rx_std_cfg = {
    .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(16000),
    .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
        I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
    .gpio_cfg = {
        .mclk = I2S_GPIO_UNUSED,
        .bclk = GPIO_NUM_41,
        .ws   = GPIO_NUM_43,
        .din  = GPIO_NUM_46,  // ASDOUT → ESP32 I2S DIN
        .dout = I2S_GPIO_UNUSED,
    },
};
rx_std_cfg.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
i2s_channel_init_std_mode(rx_handle, &rx_std_cfg);
```

**ES8311 ADC Initialization** (using esp_codec_dev):
```c
// 1. I2C control interface (GPIO8/GPIO9, already used by M5Cardputer)
// 2. Create codec device with ADC enabled
es8311_codec_cfg_t es8311_cfg = {
    .codec_mode = ESP_CODEC_DEV_WORK_MODE_ADC,  // ADC only (mic input)
    .ctrl_if = ctrl_if,
    .gpio_if = gpio_if,
    .use_mclk = false,  // ES8311 in slave mode, ESP32 provides BCLK+WS
};
const audio_codec_if_t *codec_if = es8311_codec_new(&es8311_cfg);

esp_codec_dev_cfg_t dev_cfg = {
    .codec_if = codec_if,
    .data_if = data_if,
    .dev_type = ESP_CODEC_DEV_TYPE_IN,  // Input only
};
esp_codec_dev_handle_t mic_dev = esp_codec_dev_new(&dev_cfg);

// 3. Configure for voice capture
esp_codec_dev_set_in_gain(mic_dev, 30.0f);  // +30dB PGA gain for voice
esp_codec_dev_set_sample_rate(mic_dev, 16000);
esp_codec_dev_set_in_channel(mic_dev, 1);   // Mono
esp_codec_dev_set_in_bits(mic_dev, 16);     // 16-bit
```

**Alternatives Considered**:
- **ESP-ADF**: Rejected — 200KB+ code size, heavyweight pipeline with features we don't need
- **Direct register writes**: Viable fallback. Adds ~500 lines of ES8311 datasheet-driven
  init code. Use only if esp_codec_dev integration proves incompatible with Arduino framework.
- **XiaoZhi-ESP32 AudioCodec class**: Clean C++ wrapper, but designed for XiaoZhi hardware
  (ESP32-S3-Korvo2). Would need significant adaptation for Cardputer-Adv pin map.

**Risk**: I2C bus sharing. The TCA8418RTWR keyboard expander and BMI270 IMU also use I2C
(GPIO8/GPIO9). ES8311 address (0x18) does not conflict with TCA8418 (0x34) or BMI270 (0x68).
I2C mutex required for thread-safe access.

---

### 3. USB CDC Serial within Composite Device

**Decision**: Add USB CDC ACM as the third interface in the TinyUSB composite descriptor,
providing a virtual serial port for host-to-device communication. Use newline-delimited
JSON frames at 115200 baud logical rate over the USB bulk endpoints.

**Rationale**:
- USB CDC ACM is a standard class — macOS has built-in drivers (no custom driver needed,
  same as audio and HID).
- TinyUSB supports CDC ACM as part of composite devices. The descriptor adds 2 bulk
  endpoints (IN + OUT) and 1 interrupt endpoint.
- Newline-delimited JSON is the same framing used by Claude Desktop Buddy's BLE protocol,
  making the protocol schema portable between USB and BLE transports.
- The JSON parser on-device uses ArduinoJson v7 (already a UniGeek dependency via
  M5Unified) — lightweight, well-maintained, no heap fragmentation.

**Endpoint Budget** (USB Full-Speed: max 15 IN + 15 OUT endpoints):
```text
UAC2 Audio Control:  1 IN (interrupt, 2ms) ← volume/mute status
UAC2 Audio Streaming: 1 IN (isochronous, 1ms) ← PCM audio data
HID Keyboard:        1 IN (interrupt, 1ms) ← key reports
CDC ACM:             1 IN (bulk), 1 OUT (bulk), 1 IN (interrupt, 64ms)
Total: 5 IN, 1 OUT — well within limits
```

**USB Descriptor Hierarchy**:
```text
Device Descriptor
├── Configuration Descriptor
│   ├── Interface Association Descriptor (IAD) ← groups 3 interfaces
│   │
│   ├── Interface 0: UAC2 Audio Control
│   │   ├── Class-Specific AC Interface Header
│   │   ├── Input Terminal (Microphone)
│   │   ├── Output Terminal (USB OUT)
│   │   └── Endpoint 0x81 (Interrupt IN, status)
│   │
│   ├── Interface 1: UAC2 Audio Streaming (Alt 0 = no stream, Alt 1 = stream)
│   │   └── Endpoint 0x82 (Isochronous IN, adaptive, 16kHz 16-bit mono)
│   │
│   ├── Interface 2: HID Keyboard
│   │   ├── HID Descriptor (Boot Protocol)
│   │   └── Endpoint 0x83 (Interrupt IN, 8 bytes, 1ms)
│   │
│   └── Interface 3: CDC ACM
│       ├── CDC Header + ACM + Union Functional Descriptors
│       ├── Endpoint 0x84 (Interrupt IN, notification)
│       ├── Endpoint 0x02 (Bulk OUT, data from host)
│       └── Endpoint 0x85 (Bulk IN, data to host)
```

**macOS Enumeration Order**: macOS enumerates interfaces in order. IAD groups them
under a single device entry in System Information. The device name string is set in
the USB device descriptor iProduct field.

**Alternatives Considered**:
- **BLE NUS (Nordic UART Service)**: Viable as secondary channel. Rejected as primary
  because: (1) requires pairing, (2) higher latency (10-50ms vs <1ms), (3) separate radio
  power consumption, (4) adds NimBLE stack to firmware. BLE remains a v2 option per spec.
- **Wi-Fi TCP socket**: Rejected for v1 — requires network config, higher power, shared
  2.4GHz band with potential audio interference.

---

### 4. UniGeek Codebase Analysis for Strip-Down

**Decision**: Fork lshaf/unigeek, strip to Cardputer-Adv target only, remove unneeded
features, then add UAC2 + I2S capture + CDC serial + agent UI.

**UniGeek Architecture** (Post-strip target):
```text
src/
├── main.cpp                  # KEEP: FreeRTOS tasks, app framework
├── hw/                       # KEEP: Hardware abstraction
│   ├── cardputer_adv/        # KEEP: Cardputer-Adv pin definitions
│   │   ├── pins.h            # All GPIO assignments
│   │   └── config.h          # Display, keyboard, audio config
│   └── ...                   # REMOVE: All non-Cardputer-Adv boards
├── apps/                     # PARTIALLY KEEP
│   ├── hid_keyboard/         # KEEP: USB HID keyboard relay
│   ├── badusb/               # REMOVE: BadUSB/DuckyScript engine
│   ├── wifi_tools/           # REMOVE: Wi-Fi scanning/wardriving
│   ├── webauthn/             # REMOVE: FIDO2/WebAuthn
│   ├── ir_tools/             # REMOVE: IR blaster apps
│   ├── password_mgr/         # REMOVE: Wi-Fi password manager
│   ├── ble_hid/              # REMOVE for v1: BLE keyboard (keep USB only)
│   └── ...                   # REMOVE: Other utility apps
├── lib/                      # PARTIALLY KEEP
│   ├── TFT_eSPI/             # KEEP: Display driver
│   ├── M5Cardputer/          # KEEP: Hardware library
│   └── ...                   # KEEP only what's needed
└── data/                     # KEEP: Assets, fonts
```

**Features to Remove** (estimated binary size impact):
| Feature | Est. Size | Reason |
|---------|-----------|--------|
| BadUSB/DuckyScript | ~80KB | Not needed for Claude Code Buddy |
| Wi-Fi tools (scan, deauth, wardriving) | ~120KB | No Wi-Fi for v1 |
| WebAuthn/FIDO2 | ~60KB | Out of scope |
| IR blaster apps | ~30KB | Out of scope |
| Password manager | ~40KB | Out of scope |
| BLE HID keyboard/mouse | ~50KB | USB HID only for v1 |
| Non-Cardputer-Adv board targets | ~80KB | Only Cardputer-Adv |
| Other utility apps (calculator, games) | ~40KB | Out of scope |
| **Total** | **~500KB** | From ~1.2MB → ~700KB target |

**Features to KEEP**:
| Feature | Reason |
|---------|--------|
| USB HID keyboard relay | Core feature — Cardputer keys → Mac |
| Display driver (TFT_eSPI + ST7789) | Core feature — agent status UI |
| M5Cardputer hardware layer | Keyboard scan, battery ADC, ES8311 speaker |
| SD card driver | May be needed for future audio playback |
| FreeRTOS task framework | Dual-core architecture for audio + UI |
| Menu/app framework | Reusable for UI mode switching |

**New Modules to ADD**:
| Module | Description | Est. Size |
|--------|-------------|-----------|
| usb_stack (UAC2 mic + CDC) | TinyUSB descriptors + callbacks | ~30KB |
| audio_pipeline (I2S RX) | ES8311 ADC + I2S DMA capture | ~15KB |
| display_ui (agent modes) | Status rendering + VU meter | ~20KB |
| host_comm (protocol) | JSON parser + message dispatch | ~10KB |
| **Total additions** | | **~75KB** |

**Post-modification binary target**: ~700KB (stripped base) + ~75KB (additions) = ~775KB.
Well within the 4MB firmware partition.

**Alternatives Considered**:
- **Start from scratch with ESP-IDF**: Cleaner architecture, but loses all M5Cardputer
  library support, keyboard scanning, and display drivers. Estimated ~6 weeks vs ~4 weeks.
- **Use dakshaymehta/cardputer-claude-os as base**: MicroPython-based, wrong framework.
  Would need complete rewrite in C/C++ anyway.

---

### 5. Claude Code Agent Output Parsing (Mac Daemon)

**Decision**: The Mac companion daemon monitors Claude Code terminal output via two
mechanisms: (1) Claude Code CLI stdout/stderr stream parsing for real-time status,
and (2) Claude Code API webhook/polling (if available) for structured data. Fallback
to subprocess stdout scraping.

**Rationale**:
- Claude Code runs as a terminal application. It outputs status lines to stdout that
  can be parsed for agent state changes, command entries, and output lines.
- Claude Code CLI outputs structured status lines prefixed with `⏺` (session start),
  `⏺` (thinking), `⎔` (tool call), `⏺` (response). These can be regex-matched.
- The Claude Desktop Buddy BLE protocol defines a JSON heartbeat with `total`,
  `running`, `waiting`, `msg`, `entries`, `tokens`, `tokens_today`, `prompt` fields.
  This schema is directly adaptable to our CDC serial protocol.
- For token counts specifically, Claude Code writes token usage to a local state file
  (`~/.claude/stats.json` or similar) that can be polled every 5 seconds.

**Claude Code Output Parsing Strategy**:
```python
# Key patterns to detect in Claude Code stdout:
PATTERNS = {
    'session_start': r'^⏺\s+(\w+)\s+agent',       # Agent session starting
    'tool_call':     r'^⎔\s+(.+)',                 # Tool being called
    'thinking':      r'^⏺\s+thinking',             # Claude is thinking
    'response':      r'^⏺\s+(.+)',                 # Claude response
    'permission':    r'^.*(?:approve|permission|allow)\?',  # Needs user approval
    'error':         r'^(?:Error|error|ERROR):',   # Error occurred
    'session_end':   r'^.*session (?:ended|complete)',  # Session finished
}

# State machine for tracking agent state:
IDLE → (session_start) → RUNNING
RUNNING → (permission) → WAITING_PERMISSION
RUNNING → (error) → ERROR
WAITING_PERMISSION → (approval granted) → RUNNING
WAITING_PERMISSION → (approval denied) → ERROR
ANY → (session_end) → IDLE
```

**Daemon Architecture** (Python):
```python
# ccb_daemon.py — Claude Code Buddy Mac Companion
# <200 lines target

import subprocess, serial, json, time, re, threading

class CCBDaemon:
    def __init__(self, serial_port: str):
        self.serial = serial.Serial(serial_port, 115200)
        self.state = "idle"
        self.seq = 0

    def start_agent_monitor(self):
        """Spawn Claude Code subprocess and monitor stdout."""
        self.proc = subprocess.Popen(
            ["claude"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        for line in self.proc.stdout:
            self.parse_and_forward(line)

    def parse_and_forward(self, line: str):
        """Parse Claude Code output line, update state, send JSON frame."""
        msg = self._parse_line(line)
        if msg:
            self.serial.write(json.dumps(msg).encode() + b'\n')
            self.seq += 1

    def _parse_line(self, line: str) -> dict|None:
        """State-aware line parser. Returns JSON-serializable dict or None."""
        if 'agent' in line.lower() and 'starting' in line.lower():
            self.state = "running"
            return {"type":"status", "seq":self.seq, "state":"running", ...}
        # ... additional state transitions
```

**Alternatives Considered**:
- **Claude Code API**: If Anthropic exposes a structured API for agent monitoring, this
  would be cleaner than stdout scraping. The Claude Desktop Buddy BLE protocol is the
  closest official reference. Monitor for API availability.
- **PTY/TTY hooking**: More reliable than subprocess stdout but requires macOS-specific
  PTY code. Reserve for v2 if stdout scraping proves fragile.
- **Filesystem polling**: Claude Code may write status to a state file. Polling is
  simpler but adds latency. Use as supplementary data source for token counts.

---

### 6. Display UI Design for 240×135 with Agent States

**Decision**: Implement three display modes (Agent Status, Audio VU, Idle) and four
agent states (idle, running, waiting_permission, error) using TFT_eSPI's framebuffer-less
drawing primitives. No LVGL — too heavy for 64KB heap budget on a 240×135 screen.

**Screen Layout per Mode**:

```
┌──────────────────────────────┐ 240px
│ Agent: claude-code    ⏺ RUN │  ← Mode: Agent Status
│ Runtime: 00:12:34            │     State: running
│ Tokens: 125,000 (42k today)  │
│ ───────────────────────────  │
│ > npm install                │
│ > tsc --build                │  ← Last 3 output lines
│ > jest --coverage            │
│ 12:34:56 Tests: 42/42 passed │
└──────────────────────────────┘ 135px

┌──────────────────────────────┐
│ 🔴 REC  ████████░░░░  -12dB │  ← Mode: Audio VU
│ Hold to talk...              │     (Mic active, VU meter)
│                              │
│ ───────────────────────────  │
│ Ready to transcribe          │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Cardputer-Adv      ████ 85% │  ← Mode: Idle
│ Claude Code Buddy            │     (No agent, not recording)
│                              │
│ USB: Connected               │
│ 12:34 PM  |  🔋 Charging     │
└──────────────────────────────┘

┌──────────────────────────────┐
│ ⚠ APPROVAL REQUIRED         │  ← Mode: Permission Overlay
│                              │     (Pulses red border)
│ Allow: rm -rf /tmp/build?    │
│                              │
│ [SPACE] Approve [ESC] Deny   │
└──────────────────────────────┘
```

**Mode Priority** (per Constitution III + Clarification Q1):
```text
waiting_permission > error > running > audio_input > idle
```

**Font Selection** (TFT_eSPI Adafruit GFX fonts):
- Title: FreeMonoBold9pt7b (9pt bold) — agent name, state label
- Body: FreeMono9pt7b (9pt) — runtime, token count
- Small: FreeMonoBold12pt7b — VU meter label ("REC")
- Line height at 9pt: ~14px → fits ~9 lines on 135px screen

**Rendering Strategy** (Dirty Rectangle):
- Only redraw changed regions on each status update
- Full screen redraw only on mode switch
- 15 FPS minimum for text updates, 30 FPS for VU meter animation
- Use TFT_eSPI's `drawString()` with background color fill for text updates

**Memory Budget**:
- TFT_eSPI (no framebuffer): ~2KB
- Font caches: ~8KB (3 fonts loaded)
- Status struct + render state: ~2KB
- **Display total**: ~12KB of 64KB heap budget ✅

---

## Summary of Key Decisions

| # | Decision | Choice | Fallback |
|---|----------|--------|----------|
| 1 | USB stack | TinyUSB (Espressif fork) with CFG_TUD_AUDIO=1 | Fork arduino-esp32, enable UAC2 |
| 2 | UAC2 microphone | atomic14 UAC2 descriptor patterns + custom I2S RX | esp-iot-solution ESP-IDF component |
| 3 | Audio driver | esp_codec_dev for ES8311 init + direct I2S DMA | Direct register writes |
| 4 | Host communication | USB CDC ACM + newline-delimited JSON | BLE NUS (v2 fallback) |
| 5 | Base firmware | Fork lshaf/unigeek, strip to Cardputer-Adv | Clean ESP-IDF build |
| 6 | Display UI | TFT_eSPI framebuffer-less + dirty rectangle | LovyanGFX with sprite buffer |
| 7 | Mac daemon | Python subprocess stdout scraping + regex | Claude Code API (if available) |
| 8 | Agent states | 4 states: idle, running, waiting_permission, error | Adopt Claude Desktop Buddy 7-state |
| 9 | Build system | PlatformIO + Arduino framework (UniGeek base) | Pure ESP-IDF with Arduino component |
| 10 | Protocol schema | JSON, newline-delimited, 4 message types | Protocol Buffers (if JSON too large) |
