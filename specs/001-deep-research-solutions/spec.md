# Feature Specification: Solution Options Research — Cardputer-Adv Firmware

**Feature Branch**: `001-deep-research-solutions`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "deep research and generate solutions options for Cardputer-Adv Claude Code Buddy firmware — USB composite device (mic + keyboard) with screen UI for CLI agent status"

## Clarifications

### Session 2026-06-06

- Q: What is the complete set of CLI agent states the Cardputer screen should visually distinguish? → A: `idle`, `running`, `waiting_permission`, `error` (4 states)
- Q: Is the Mac companion script in scope for v1, and who is responsible for building it? → A: In scope for v1. The spec and plan MUST include a minimal Mac companion daemon (Python script) that reads Claude Code output and forwards status frames to the Cardputer serial port. Delivered alongside firmware.
- Q: Which existing GitHub repository should serve as the foundation to fork/modify? → A: [lshaf/unigeek](https://github.com/lshaf/unigeek) — Cardputer-ADV multi-tool firmware. PlatformIO + Arduino + TFT_eSPI. Best Cardputer-Adv hardware coverage (TCA8418 keyboard, ES8311 audio, ST7789 display, USB HID, SD card). Main gap: no UAC2 microphone — needs TinyUSB UAC2 descriptor + I2S mic capture pipeline added.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Evaluate USB Composite Device Approaches (Priority: P1)

As a firmware architect, I need a clear comparison of USB stack options that can deliver UAC2
microphone + HID keyboard composite device functionality on ESP32-S3, so I can select the
approach with the best chance of stable macOS enumeration without custom drivers.

**Why this priority**: The USB composite device is the core value proposition. If the
Cardputer-Adv doesn't enumerate reliably as both mic and keyboard on macOS, the entire
product concept fails. This decision gates all other firmware work.

**Independent Test**: Each option can be evaluated by flashing a minimal proof-of-concept
firmware and verifying that macOS System Information (`system_profiler SPUSBDataType`)
shows both an Audio input device and a HID keyboard under a single USB composite device
entry.

**Acceptance Scenarios**:

1. **Given** the Cardputer-Adv is connected via USB-C to a Mac running macOS 15+,
   **When** the firmware boots, **Then** the device enumerates as a USB composite device
   with at least two interfaces (Audio Class and HID) within 3 seconds.
2. **Given** the composite device is enumerated, **When** the user speaks into the MEMS
   microphone, **Then** macOS System Settings → Sound → Input shows "Cardputer-Adv" as an
   available microphone with active level meter movement.
3. **Given** the composite device is enumerated, **When** a key on the Cardputer-Adv
   keyboard is pressed, **Then** the corresponding HID keycode is received by the active
   macOS application within 5ms.
4. **Given** the USB cable is physically disconnected, **When** it is reconnected,
   **Then** the device re-enumerates correctly without requiring a power cycle or reset
   button press.

---

### User Story 2 — Select Audio Pipeline Architecture (Priority: P1)

As a firmware developer, I need to understand the trade-offs between different ES8311 audio
codec driver approaches (ESP-IDF codec component, ESP-ADF, community libraries, direct
register access) so I can choose the audio pipeline that balances development effort
against latency and reliability.

**Why this priority**: Audio capture quality and latency directly determine whether voice
transcription (via MacWhisper) produces accurate results. An audio pipeline with high
latency or glitches makes the device unusable for voice-to-text workflows.

**Independent Test**: Each approach can be evaluated by capturing 10 seconds of audio from
the MEMS mic, streaming it to the host via UAC2, and measuring: (a) end-to-end latency from
sound to USB packet, (b) sample drop rate, (c) SNR compared to the built-in MacBook mic.

**Acceptance Scenarios**:

1. **Given** the ES8311 is configured for 16-bit 16kHz mono capture, **When** audio is
   streamed to the host, **Then** end-to-end latency (mic membrane to USB UAC2 endpoint) is
   under 30ms.
2. **Given** continuous audio streaming for 10 minutes, **When** the sample stream is
   analyzed, **Then** zero dropped or corrupted samples are detected.
3. **Given** the audio pipeline is active, **When** the HID keyboard simultaneously sends
   key reports, **Then** no audio glitches (pops, clicks, gaps) are introduced.
4. **Given** the microphone is capturing in a quiet room, **When** the captured audio is
   compared to the MacBook built-in mic, **Then** the SNR is within 5dB of the MacBook mic
   or better.

---

### User Story 3 — Choose Display/UI Framework (Priority: P2)

As a UX designer and firmware developer, I need to compare display library options
(M5Unified/Arduino_GFX, TFT_eSPI, LVGL, LovyanGFX) for rendering the CLI agent status UI
on the 240×135 ST7789V2 screen, so I can select the library that delivers readable text and
smooth status transitions without exceeding the ESP32-S3's memory budget.

**Why this priority**: The screen is the primary user feedback channel — it shows what the
CLI agent is doing without requiring the user to look at the Mac monitor. A poor display
choice leads to unreadable text, slow updates, or memory exhaustion.

**Independent Test**: Each library can be evaluated by rendering a mock CLI agent status
screen (agent name, runtime counter, token count, last output line) at target frame rates
and measuring: (a) frames per second, (b) heap memory consumed, (c) code complexity (lines
of setup code).

**Acceptance Scenarios**:

1. **Given** the status UI is rendering, **When** measured over 60 seconds, **Then** the
   display updates at a minimum of 15 FPS for text-only status and 30 FPS for animated
   elements (VU meter, spinner).
2. **Given** the UI library is initialized with the status screen, **When** free heap is
   measured, **Then** at least 64KB of free heap remains for audio and USB stacks.
3. **Given** text in multiple sizes (title, body, small status), **When** viewed on the
   240×135 display, **Then** all text is readable at arm's length with at least 3 visible
   lines of agent output.
4. **Given** the agent status changes (new output line, token count update), **When** the
   display updates, **Then** the transition is visually smooth (no flickering, tearing,
   or full-screen redraw artifacts).

---

### User Story 4 — Define Host Communication Protocol (Priority: P2)

As a system integrator, I need to design the communication channel between the Mac host
(Claude Code / CLI agent) and the Cardputer-Adv firmware, so that agent status, token
counts, and process information can be forwarded to the Cardputer screen in real time.

**Why this priority**: The screen is only useful if it has data to display. The host
communication protocol determines how rich and timely the displayed agent status can be.

**Independent Test**: Each communication method can be evaluated by running a test script
on the Mac that sends mock agent status updates (matching the proposed protocol schema) and
measuring: (a) end-to-end latency from script send to screen render, (b) reliability under
USB bus contention, (c) implementation complexity on both host and device sides.

**Acceptance Scenarios**:

1. **Given** the Mac companion script sends an agent status message, **When** the
   Cardputer-Adv receives it, **Then** the status is rendered on screen within 200ms of
   the send call.
2. **Given** the communication channel is active, **When** 1000 status messages are sent
   in rapid succession, **Then** zero messages are dropped or corrupted (verified by
   sequence numbering).
3. **Given** the host communication channel drops (e.g., serial port closed), **When** the
   Cardputer-Adv detects the drop, **Then** the display shows a "Disconnected" status
   within 2 seconds without crashing or hanging.
4. **Given** the communication channel recovers, **When** the host reconnects, **Then**
   status updates resume automatically without a device reset.

---

### User Story 5 — Compare Firmware Frameworks (Priority: P3)

As the project lead, I need a decision framework comparing Arduino (via PlatformIO) against
ESP-IDF for this specific project, accounting for USB composite device support, audio
driver availability, library ecosystem, debugging capabilities, and long-term
maintainability.

**Why this priority**: The framework choice affects every line of firmware code. While the
USB and audio decisions are more urgent (P1), the framework choice must be made before
significant implementation begins.

**Independent Test**: Each framework can be evaluated by implementing a minimal "hello
world" that initializes the display, reads a keypress, and sends a USB HID report —
measuring: (a) lines of code, (b) binary size, (c) compile time, (d) debug setup time.

**Acceptance Scenarios**:

1. **Given** a developer new to the project, **When** they follow the setup instructions,
   **Then** they can build and flash the firmware within 30 minutes (including toolchain
   installation time).
2. **Given** the firmware is built with the selected framework, **When** a crash occurs,
   **Then** the developer can identify the root cause using stack trace / core dump within
   10 minutes.
3. **Given** a library dependency needs updating, **When** the update is applied,
   **Then** the full project rebuilds in under 2 minutes on a modern MacBook.

---

### Edge Cases

- What happens when both audio streaming and HID key reports contend for the USB bus?
- How does the firmware handle a Mac host that suspends/resumes (lid close/open)?
- What happens if the ES8311 codec doesn't respond on the I2C bus (hardware fault)?
- Can the device operate in "keyboard-only" or "mic-only" mode if one USB interface fails
  to enumerate?
- How does the firmware behave when connected to a USB-C power-only cable (no data lines)?
- What is the behavior when connected to a USB hub vs direct Mac USB-C port?
- How does battery charging interact with USB device mode (charging while enumerating)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST evaluate at least 3 distinct USB stack options and produce a
  scored comparison covering: macOS enumeration reliability, UAC2 microphone support, HID
  keyboard support, composite device support, and maintenance status
- **FR-002**: The system MUST evaluate ES8311 audio codec driver approaches and produce a
  comparison covering: latency, CPU overhead, memory usage, sample rate flexibility, and
  integration complexity
- **FR-003**: The system MUST evaluate display/UI library options for the ST7789V2
  240×135 screen and produce a comparison covering: frame rate, memory usage, text
  rendering quality, widget/graph capability, and Cardputer-Adv compatibility
- **FR-004**: The system MUST design and document a host-to-device communication protocol
  schema (message format, framing, error detection) for relaying CLI agent status. The
  protocol MUST support all 4 agent states (idle, running, waiting_permission, error).
- **FR-004a**: The system MUST include a Mac companion daemon (Python script) that reads
  Claude Code terminal output and forwards structured JSON status frames to the Cardputer
  USB CDC serial port. The daemon MUST handle: Claude Code session start/stop detection,
  token count extraction, command listing, and output line capture.
- **FR-005**: The system MUST produce a firmware framework decision matrix (Arduino vs
  ESP-IDF vs Hybrid) with scored criteria weighted for this project's specific needs
- **FR-006**: The system MUST document all assumptions and identify areas requiring
  proof-of-concept validation before final architecture commitment
- **FR-007**: The system MUST provide a recommended architecture stack with a phased
  implementation roadmap (Phase 1: core USB enumeration → Phase 2: audio pipeline →
  Phase 3: display UI → Phase 4: host communication → Phase 5: power management)
- **FR-008**: Each solution option MUST include a risk assessment identifying the primary
  technical risk and its mitigation strategy

### Key Entities

- **USB Stack Option**: A specific library/framework for implementing USB device mode on
  ESP32-S3, characterized by: name, version, UAC2 support (yes/no/partial), HID support
  (yes/no), composite support (yes/no), macOS compatibility notes, license, and community
  activity level
- **Audio Pipeline Architecture**: An end-to-end audio capture chain from MEMS mic to USB
  UAC2 endpoint, characterized by: codec driver approach, I2S configuration, buffer
  strategy, latency budget, and CPU utilization
- **Display/UI Framework**: A library for rendering pixels on the ST7789V2, characterized
  by: API style, rendering pipeline (framebuffer vs direct), widget library, font support,
  and PSRAM requirement
- **Host Communication Protocol**: A message schema and transport binding, characterized
  by: serialization format, framing mechanism, message types, error handling, and
  host-side implementation requirements
- **Firmware Framework**: The build system and runtime environment, characterized by:
  toolchain, library ecosystem, debugging support, binary size, and hardware abstraction
  layer

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The research report provides sufficient information for a firmware architect
  to commit to a full technical stack without further broad research (all major
  alternatives explored, trade-offs documented)
- **SC-002**: At least 2 viable USB stack approaches are identified with working
  proof-of-concept code references (GitHub repositories, Espressif examples) that
  demonstrate UAC2 + HID composite on ESP32-S3
- **SC-003**: The recommended audio pipeline architecture has a clearly documented
  latency budget showing how the 30ms end-to-end target is achievable
- **SC-004**: The recommended display framework can render a prototype CLI agent status
  screen within the 64KB free heap constraint, with frame rate measurements from
  comparable ESP32-S3 projects
- **SC-005**: The host communication protocol schema is concrete enough that a developer
  can implement both the device-side parser and the host-side sender without ambiguity
- **SC-006**: The firmware framework decision matrix includes at least 5 weighted criteria
  with explicit scores and justifications for each option
- **SC-007**: All research findings include source references (URLs, repository names,
  version numbers) so they can be verified and revisited as the ecosystem evolves

## Assumptions

- The Cardputer-Adv is connected via a USB-C cable that supports USB 2.0 data (not
  charge-only). This is the default for the included cable and standard USB-C cables.
- The target Mac host is an Apple Silicon MacBook (M1 or newer) running macOS 15 Sequoia
  or later with MacWhisper installed and configured to use Right Command or Right Option
  as the dictation trigger key.
- The Cardputer-Adv ESP32-S3FN8 does NOT have PSRAM. All firmware must fit within the
  internal 512KB SRAM (with ~320KB available to user code after framework overhead).
- The firmware does not need to support Windows or Linux hosts in the initial version
  (macOS-only for v1), but the USB descriptors should follow standards to enable future
  cross-platform support.
- Voice-to-text transcription happens entirely on the Mac (MacWhisper using local Whisper
  models). The Cardputer-Adv is a "dumb" USB peripheral — it streams raw audio and sends
  HID keycodes; it does not perform any on-device speech recognition.
- The companion script on the Mac that forwards CLI agent status to the Cardputer is a
  required v1 deliverable alongside the firmware. It reads Claude Code terminal output
  (via stdout parsing or Claude Code API hooks) and forwards structured JSON status
  frames to the Cardputer USB CDC serial port. Implementation: Python script or small
  daemon, target <200 lines of code.
- Battery life with continuous audio streaming + display on is expected to be 2-4 hours
  on the 1750mAh battery. USB-powered operation is the primary use case.
- The ST7789V2 display backlight shares power with the RGB LED on Cardputer-Adv. The
  firmware must account for this shared power domain.

## Solution Options Research *(findings from deep research)*

### 1. USB Composite Device — Stack Comparison

| Criterion | TinyUSB (upstream) | chegewara/EspTinyUSB | ESP-IDF USB Device (esp-iot-solution) | Arduino USB (HW CDC+MSC+HID) |
|---|---|---|---|---|
| UAC2 Microphone | ✅ Class driver exists | ⚠️ Partial (needs porting) | ✅ UAC driver in esp-iot-solution v2.0 | ❌ Not supported (issue #12053) |
| HID Keyboard | ✅ Mature | ✅ Mature, many examples | ✅ Supported | ✅ Mature (built-in) |
| Composite Device | ✅ Configurable descriptors | ✅ Examples for HID+CDC+MSC | ✅ Supported | ⚠️ Limited (CDC+HID only) |
| ESP32-S3 Support | ⚠️ Needs board config | ✅ Primary target | ✅ Native Espressif | ✅ Built into arduino-esp32 |
| macOS Enumeration | ✅ Standards-compliant | ✅ Verified by community | ✅ Espressif-tested | ✅ Verified |
| Maintenance | ✅ Active (upstream TinyUSB) | ⚠️ Single maintainer | ✅ Espressif-backed | ✅ Part of arduino-esp32 core |
| Documentation | ✅ Good | ⚠️ Sparse, example-driven | ✅ Good (Espressif docs) | ✅ Good |

**Primary Risk**: UAC2 support is the constraint. Arduino USB stack does NOT support it.
TinyUSB upstream has the class driver but needs ESP32-S3 board plumbing. The Espressif
esp-iot-solution provides the most integrated path but may limit framework choice to
ESP-IDF.

**Recommended Approach**: ESP-IDF with Espressif's TinyUSB fork (used in esp-iot-solution)
for the composite device descriptor. This gives UAC2 + HID with native Espressif support.
If Arduino framework is chosen for other reasons, use the hybrid Arduino-as-component
approach within an ESP-IDF project.

### 2. Audio Pipeline — ES8311 Driver Options

| Criterion | esp_codec_dev (ESP-IDF) | ESP-ADF | XiaoZhi-ESP32 (community) | Direct Register (bare metal) |
|---|---|---|---|---|
| Latency | Low (I2S DMA) | Medium (ADF pipeline overhead) | Low (thin wrapper) | Lowest (no overhead) |
| Development Effort | Medium | Low (high-level API) | Low (C++ class) | High (datasheet-driven) |
| CPU Overhead | ~5% for I2S + I2C | ~15-20% (pipeline, resampling) | ~5% | ~3% |
| Code Size | ~15KB | ~200KB+ (full ADF) | ~10KB | ~5KB |
| Maintenance | Espressif official | Espressif official | Community, active 2025 | N/A (your code) |
| Audio Quality Control | Volume, mute, PGA gain | Full pipeline (EQ, resample, AEC) | Volume, mute | Full control |
| Cardputer-Adv Pin Map | Needs custom GPIO config | Needs board definition | Needs adaptation | Full control |

**Recommended Approach**: `esp_codec_dev` component for ES8311 initialization and control,
with direct I2S DMA driver for the data path. This avoids the heavyweight ESP-ADF while
getting tested, maintained codec init sequences. The I2S driver reads from the ES8311's
ADC output pin (ASDOUT on GPIO46) via standard I2S DMA.

### 3. Display/UI Framework — Comparison

| Criterion | TFT_eSPI | LovyanGFX | M5Unified/Arduino_GFX | LVGL |
|---|---|---|---|---|
| ST7789 Support | ✅ Excellent, fast | ✅ Excellent, sprite-based | ✅ Built-in for M5Stack | ✅ Via display driver |
| 240×135 Fit | ✅ Perfect | ✅ Perfect | ✅ Native Cardputer support | ⚠️ Overkill for this res |
| Frame Rate | 30-60 FPS (DMA SPI) | 30-60 FPS (DMA SPI) | 20-30 FPS | 15-25 FPS (widget overhead) |
| RAM Usage | ~2KB (no framebuffer) | ~10KB (sprite buffer) | ~32KB (framebuffer) | ~48KB+ (display + widgets) |
| Font Support | Adafruit GFX fonts + custom | Adafruit GFX + TTF | Adafruit GFX + M5Stack fonts | TTF, built-in, custom |
| Cardputer-Adv Compat | Manual pin config needed | Manual pin config needed | ✅ Direct support via M5Cardputer | Manual driver needed |
| Widgets/UI | None (raw drawing) | None (raw drawing) | Basic (M5Stack helpers) | Full (buttons, labels, charts) |
| Community Size | Very large | Medium (Japan) | Large (M5Stack ecosystem) | Very large |

**Recommended Approach**: **TFT_eSPI** for maximum performance with minimal RAM. The
240×135 screen doesn't need LVGL's widget overhead. For the three UI modes (agent status,
audio VU, idle), custom drawing with TFT_eSPI provides the best FPS-to-RAM ratio. If
richer widgets are needed later, LovyanGFX offers a middle ground with sprite acceleration.

TFT_eSPI pin configuration for Cardputer-Adv ST7789V2:
```cpp
#define ST7789_DRIVER
#define TFT_WIDTH  240
#define TFT_HEIGHT 135
#define TFT_CS   37
#define TFT_DC   34
#define TFT_MOSI 35
#define TFT_SCLK 36
#define TFT_BL   38
#define TFT_RST  33
#define SPI_FREQUENCY 40000000
```

### 4. Host Communication Protocol — Design

Three transport options evaluated:

| Criterion | USB CDC Serial | BLE (Nordic UART Service) | Wi-Fi (TCP/HTTP) |
|---|---|---|---|
| Latency | <1ms | 10-50ms | 5-100ms |
| Reliability | Deterministic | Good (LE Credit) | Variable |
| Power | Negligible (bus-powered) | ~150mA BLE active | ~130mA Wi-Fi active |
| Host Setup | No pairing needed | Pairing + bonding | Network config |
| Security | Physical (USB cable) | LE Secure Connections | TLS required |
| Concurrent with Audio+HID | ✅ Same USB bus | ✅ Independent radio | ⚠️ Shared 2.4GHz |
| Implementation Complexity | Low (CDC ACM class) | Medium (NimBLE stack) | High (Wi-Fi + HTTP/TCP) |

**Recommended Approach**: **USB CDC Serial** as primary channel. The device already
connects via USB-C — adding serial communication on a third USB interface (CDC ACM)
alongside Audio and HID is a natural fit with zero additional pairing or network
configuration. BLE can be added as an optional secondary channel for wireless status
monitoring when the device is not physically connected.

**Proposed Protocol Schema** (JSON over newline-delimited frames):

```json
{
  "type": "status",
  "seq": 42,
  "agent": "claude-code",
  "state": "running",
  "msg": "Installing dependencies...",
  "tokens": 125000,
  "tokens_today": 42000,
  "entries": ["npm install", "tsc --build", "jest --coverage"],
  "last_output": "Tests passed: 42/42"
}
```

Message types: `status` (periodic heartbeat), `permission` (approval request), `log`
(terminal output line), `config` (host→device settings).

**Agent States** (4-state taxonomy):

| State | Display Behavior | Trigger |
|-------|-----------------|---------|
| `idle` | Show connection status, battery, clock. Idle mode per Constitution III. | No agent session active. |
| `running` | Show agent name, runtime counter, token count, last output line. Agent Status mode per Constitution III. | Agent is executing tasks; no user intervention needed. |
| `waiting_permission` | Show permission prompt (e.g., "Approve `rm -rf`?"). Pulse/highlight border. Highest priority — overrides running display. | Agent issued a tool call requiring user approval. |
| `error` | Show error icon, last error message. Alternating with previous state every 3 seconds. | Agent session crashed, tool call failed fatally, or host communication lost. |

State priority for display (highest to lowest): `waiting_permission` > `error` > `running` > `idle`.

### 5. Firmware Framework — Decision Matrix

| Criterion | Weight | Arduino (PlatformIO) | ESP-IDF (Native) | Arduino-as-Component (Hybrid) |
|---|---|---|---|---|
| USB Composite Device (UAC2+HID) | 5 | ⭐⭐ (Arduino USB no UAC2) | ⭐⭐⭐⭐⭐ (Full TinyUSB) | ⭐⭐⭐⭐ (ESP-IDF USB + Arduino libs) |
| Audio Driver (ES8311) | 4 | ⭐⭐ (Port ESP-IDF component) | ⭐⭐⭐⭐⭐ (esp_codec_dev) | ⭐⭐⭐⭐⭐ (esp_codec_dev) |
| Display Library Availability | 3 | ⭐⭐⭐⭐⭐ (TFT_eSPI, M5 libs) | ⭐⭐⭐ (Port TFT_eSPI) | ⭐⭐⭐⭐⭐ (All Arduino libs) |
| Debugging (JTAG, Core Dump) | 3 | ⭐⭐ (Serial only) | ⭐⭐⭐⭐⭐ (Full OpenOCD) | ⭐⭐⭐⭐ (ESP-IDF debug tools) |
| Dev Setup Time | 2 | ⭐⭐⭐⭐⭐ (20 min) | ⭐⭐⭐ (1 hr) | ⭐⭐ (2 hr, complex config) |
| M5Cardputer Library Reuse | 3 | ⭐⭐⭐⭐⭐ (Direct use) | ⭐ (Rewrite needed) | ⭐⭐⭐⭐⭐ (Direct use) |
| Community/Examples | 2 | ⭐⭐⭐⭐⭐ (Cardputer specific) | ⭐⭐⭐ (ESP32-S3 general) | ⭐⭐⭐ (Both ecosystems) |
| Long-term Maintenance | 4 | ⭐⭐⭐ (Core 3.x migration) | ⭐⭐⭐⭐⭐ (Espressif roadmap) | ⭐⭐⭐ (Two build systems) |
| **Weighted Score** | | **3.0 / 5** | **4.1 / 5** | **4.2 / 5** |

**Recommended Approach**: **Arduino-as-Component (Hybrid)** for v1. This uses ESP-IDF as
the base build system (getting full TinyUSB and ES8311 driver support) while including
Arduino as a component, which makes the M5Cardputer library (keyboard, display, battery)
and TFT_eSPI directly usable. The build configuration is more complex initially but
provides the best of both ecosystems.

For v2+ with production hardening, migrate fully to ESP-IDF with native driver
implementations to eliminate the Arduino dependency.

### Phase 0 Proof-of-Concept Priorities (UniGeek-Based)

Before committing to the full architecture, these POCs validate the key gaps in UniGeek:

1. **UAC2 Microphone on UniGeek** (Highest Priority): Add TinyUSB UAC2 microphone descriptor
   to UniGeek's existing USB HID stack. Verify macOS enumerates BOTH audio input AND HID
   keyboard. Use UAC2 descriptor patterns from atomic14/esp32-usb-uac-experiments.
   Target: 1 day.
2. **ES8311 Mic Capture POC**: Configure ES8311 ADC path (ASDOUT on GPIO46) for 16-bit
   16kHz mono I2S capture. Verify PCM samples via serial dump. Target: 1 day.
3. **Audio-to-UAC2 Pipeline**: Connect ES8311 I2S RX DMA → TinyUSB UAC2 TX endpoint.
   Verify macOS receives clean audio. Target: 2 days.
4. **CDC Serial + Agent UI POC**: Add USB CDC ACM interface to composite descriptor.
   Render mock agent status on TFT_eSPI display, updated via JSON frames from Python
   test script. Target: 2 days.
5. **UniGeek Strip-Down**: Remove unneeded features (BadUSB, Wi-Fi tools, WebAuthn, IR
   apps, non-Cardputer-Adv boards). Verify binary size reduction and all retained
   features still work. Target: 1 day.

Total Phase 0 effort: approximately 7 working days for all five validations.

### 6. Base Project Analysis — GitHub Candidates for Fork/Modify

Extensive GitHub search identified 8 candidate repositories evaluated against the
constitution principles and technical constraints. Full evaluation below.

#### Selected Base: lshaf/unigeek ⭐

| Attribute | Assessment |
|-----------|-----------|
| **URL** | <https://github.com/lshaf/unigeek> |
| **Build System** | PlatformIO + Arduino framework |
| **Target** | M5Stack Cardputer-ADV (primary), Cardputer v1.1, plus 15+ other ESP32 handhelds |
| **License** | GPL-3.0 |
| **Stars/Activity** | Active development (2025-2026) |

**What UniGeek already provides (matched to our modules):**

| Module | Coverage | Details |
|--------|----------|---------|
| `keyboard` | ✅ 100% | TCA8418RTWR I2C scan via M5Cardputer library; physical→USB HID relay works today |
| `usb_stack` (HID) | ✅ 80% | USB HID keyboard + mouse + consumer control already working via Arduino USB stack |
| `usb_stack` (UAC2) | ❌ 0% | **Gap**: No USB audio. Must add TinyUSB UAC2 descriptor + I2S mic capture |
| `audio_pipeline` (output) | ✅ 70% | I2S speaker output via ES8311 working (M5Cardputer.Speaker API) |
| `audio_pipeline` (input) | ❌ 10% | **Gap**: ES8311 ADC/mic path not implemented. Must add I2S RX DMA from ES8311 ASDOUT (GPIO46) |
| `display_ui` | ✅ 90% | TFT_eSPI with full ST7789V2 240×135 support; multi-screen app framework exists |
| `host_comm` | ❌ 0% | **Gap**: No USB CDC serial agent protocol. Must add CDC ACM interface + JSON parser |
| `power_mgmt` | ✅ 80% | Battery ADC via M5Cardputer.Power API; charging detection |

**Estimated modification effort**: ~2 weeks to add UAC2 mic, I2S capture, CDC serial, and agent UI on top of UniGeek base, vs ~4 weeks from scratch.

#### Runner-Up Candidates

**A. atomic14/esp32-usb-uac-experiments** (<https://github.com/atomic14/esp32-usb-uac-experiments>)
- ESP-IDF project with WORKING UAC2 microphone + speaker on ESP32-S3 using TinyUSB
- Best UAC2 reference code available — USE AS REFERENCE for USB audio descriptors
- **Verdict**: Don't fork, but copy UAC2 TinyUSB descriptor + audio callback patterns

**B. dakshaymehta/cardputer-claude-os** (<https://github.com/dakshaymehta/cardputer-claude-os>)
- UIFlow2/MicroPython. Claude Buddy (BLE), Push-to-Claude (Wi-Fi voice → Whisper), Claude Pager
- Complete Claude agent integration with Cloudflare Workers backend
- **Verdict**: Don't fork (wrong framework — MicroPython, not C/C++). USE AS REFERENCE for Claude integration patterns, BLE protocol, and agent state UX

**C. anthropics/claude-desktop-buddy** (<https://github.com/anthropics/claude-desktop-buddy>)
- Official Anthropic reference. PlatformIO + Arduino. 7-state machine, BLE NUS protocol, board HAL pattern
- Clean architecture: `main.cpp` + `ble_bridge.cpp` + `buddies/` + `boards/` + `hw/`
- **Verdict**: Don't fork (M5StickC Plus target, no audio/HID). USE AS REFERENCE for: state machine pattern, BLE protocol schema, NVS persistence pattern, board abstraction layer design

**D. Espressif esp-iot-solution — USB Device UAC** (<https://github.com/espressif/esp-iot-solution>)
- Official Espressif UAC2 device driver (ESP-IDF). Configurable sample rate, mic/speaker channels
- **Verdict**: USE AS REFERENCE for TinyUSB UAC2 configuration and descriptor setup

**E. AndyAiCardputer/mp3-player-winamp-cardputer-adv** (<https://github.com/AndyAiCardputer/mp3-player-winamp-cardputer-adv>)
- Cardputer-Adv specific: ES8311 speaker output via M5Cardputer.Speaker API, ST7789 display via M5GFX
- Confirms ES8311 integration pattern and FreeRTOS dual-core task architecture
- **Verdict**: USE AS REFERENCE for ES8311 audio output configuration and dual-core task setup

**F. probudhabishayee/INMP441-with-ESP32-S3-USB-Microphone** (<https://github.com/probudhabishayee/INMP441-with-ESP32-S3-USB-Microphone>)
- ESP32-S3 USB microphone using INMP441 I2S MEMS mic + TinyUSB UAC2
- Closest working example to our mic capture pipeline (different mic, same architecture)
- **Verdict**: USE AS REFERENCE for I2S → UAC2 data flow pattern

#### Reference Code Strategy

```text
Base to fork:    lshaf/unigeek          → Cardputer-Adv hardware, USB HID, display, ES8311 speaker
Copy UAC2 from:  atomic14/esp32-usb-uac  → TinyUSB UAC2 descriptors + audio callbacks
Copy I2S RX from: probadhabishayee/INMP441-ESP32-S3-USB → I2S → UAC2 mic data flow
Adopt protocol:  anthropics/claude-desktop-buddy → JSON state machine + BLE schema (adapted for USB CDC)
Verify ES8311:   AndyAiCardputer/mp3-player → ES8311 init sequences confirmed working on Cardputer-Adv
```

#### UniGeek Features to Remove (for our firmware)

When forking UniGeek, these features should be stripped to reduce binary size and complexity:
- DuckyScript / BadUSB engine (not needed for our use case)
- Wi-Fi password manager / wardriving tools
- WebAuthn / FIDO2 passkey
- IR blaster apps
- BLE keyboard/mouse (keep USB HID only for v1)
- All non-Cardputer-Adv board targets (keep only the K132-Adv HAL)

Estimated binary size reduction: ~40% (from ~1.2MB to ~700KB), leaving ample flash for UAC2 + CDC serial + agent UI additions.

## Dependencies

- **Base Firmware**: [lshaf/unigeek](https://github.com/lshaf/unigeek) (GPL-3.0) — forked
  and stripped down as the foundation. Provides Cardputer-Adv hardware drivers, USB HID,
  TFT_eSPI display, ES8311 speaker output, battery ADC.
- **UAC2 Reference**: [atomic14/esp32-usb-uac-experiments](https://github.com/atomic14/esp32-usb-uac-experiments) —
  TinyUSB UAC2 descriptor patterns and audio callback architecture (code copied, not forked).
- **I2S Mic Reference**: [probadhabishayee/INMP441-with-ESP32-S3-USB-Microphone](https://github.com/probadhabishayee/INMP441-with-ESP32-S3-USB-Microphone) —
  I2S → UAC2 data flow pattern (code copied, not forked).
- **Protocol Reference**: [anthropics/claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy) —
  JSON state machine, BLE protocol schema adapted for USB CDC serial (pattern adopted, not forked).
- **ES8311 Verification**: [AndyAiCardputer/mp3-player-winamp-cardputer-adv](https://github.com/AndyAiCardputer/mp3-player-winamp-cardputer-adv) —
  Confirms ES8311 init sequences on Cardputer-Adv hardware.
- **External**: `espressif/esp_codec_dev` component (ESP Component Registry) for ES8311
  driver
- **External**: TFT_eSPI library (Bodmer) for display — already integrated in UniGeek
- **External**: M5Cardputer + M5Unified Arduino libraries — already integrated in UniGeek
- **External**: macOS 15+ with MacWhisper installed for end-to-end testing
- **Internal**: Constitution v1.0.0 (USB Composite Device First, Hardware-Native
  Performance, Screen-First UX, Reliable Connection, Modular Architecture)

## Out of Scope

- On-device speech recognition or Whisper inference (all voice-to-text runs on Mac)
- BLE or Wi-Fi communication (USB-only for v1; wireless is v2)
- Custom bootloader or OTA firmware updates (v1 uses USB cable flashing)
- Windows or Linux host support (macOS-only for v1)
- Audio output / speaker playback (mic input only for v1; speaker may be added later)
- Security hardening (secure boot, flash encryption) — v2 consideration
- Physical enclosure modifications or 3D-printed accessories
