# Implementation Plan: Solution Options Research — Cardputer-Adv Firmware

**Branch**: `001-deep-research-solutions` | **Date**: 2026-06-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-deep-research-solutions/spec.md`

**Note**: This plan covers the RESEARCH PHASE — generating comprehensive solution
documentation, PRD, and an execution roadmap. The actual firmware implementation
will be planned in a subsequent feature spec (`/speckit-specify` for the firmware build).

## Summary

This feature delivers a comprehensive technical research report that evaluates all viable
approaches for building the Cardputer-Adv Claude Code Buddy firmware. The primary output
is a set of documents that enable a firmware architect to commit to a full technical stack
without further broad research.

The research covers five technical dimensions (USB composite device, audio pipeline,
display/UI, host communication, firmware framework), evaluates 8 GitHub repositories as
potential bases, selects **lshaf/unigeek** as the foundation to fork, and produces a
concrete execution roadmap with 5 Phase 0 proof-of-concept validations.

Final outputs: solution options comparison (in spec.md), research.md (deep technical
analysis), data-model.md (protocol & state machine), contracts/ (USB descriptor, HID
reports, audio format, host protocol), quickstart.md (developer onboarding), and this
plan.md (execution roadmap).

## Technical Context

**Language/Version**: C++17 (firmware), Python 3.11+ (Mac companion daemon)

**Primary Dependencies**:
- **Firmware base**: lshaf/unigeek (PlatformIO + Arduino framework, GPL-3.0)
- **USB stack**: TinyUSB (via Espressif fork, UAC2 + HID + CDC composite)
- **Audio driver**: esp_codec_dev (ESP Component Registry v1.3.4+) for ES8311
- **Display**: TFT_eSPI (Bodmer) — already integrated in UniGeek
- **Hardware libs**: M5Cardputer v1.1.1+, M5Unified v0.2.10+
- **Protocol**: ArduinoJson v7.0.0+ (JSON parsing on device)
- **Mac daemon**: Python stdlib (pyserial, subprocess) — <200 lines target
- **UAC2 reference**: atomic14/esp32-usb-uac-experiments (code copied, not forked)
- **Protocol reference**: anthropics/claude-desktop-buddy (state machine pattern adopted)

**Storage**: NVS (Non-Volatile Storage) for device config; LittleFS for assets if needed.
No on-device audio storage — audio streams raw over USB.

**Testing**:
- **Host unit tests**: Unity or doctest (C++) for firmware modules with mocked hardware
- **Hardware integration**: Physical Cardputer-Adv + macOS `system_profiler SPUSBDataType`
- **End-to-end**: USB plug → MacWhisper trigger → speak → verify transcribed text
- **Protocol tests**: Python test script sending mock agent status frames → verify display

**Target Platform**: ESP32-S3FN8 (M5Stack Cardputer-Adv, SKU: K132-Adv) + macOS 15+ (Apple Silicon)

**Project Type**: Embedded firmware (ESP32-S3) + host companion daemon (macOS Python script)

**Performance Goals**:
- Audio pipeline latency: <30ms (mic membrane → USB UAC2 endpoint)
- USB enumeration: <3s (full composite: Audio + HID + CDC)
- Display refresh: 15 FPS (status), 30 FPS (VU meter animation)
- HID key report: <5ms from physical keypress
- Free heap floor: 64KB at all times

**Constraints**:
- No PSRAM (ESP32-S3FN8: 512KB SRAM, ~320KB available to user code)
- USB Full-Speed (12 Mbps) shared between audio (256 kbps), HID (8-byte reports), CDC serial
- Single USB-C cable for power + data — no separate power supply
- macOS-only host for v1 (USB standards-compliant descriptors for future cross-platform)
- Binary size target: <1MB (fits within 4MB firmware partition with headroom)
- Battery: 1750mAh, 2-4 hours continuous operation, USB-powered primary use case

**Scale/Scope**:
- 1 device type (Cardputer-Adv), 1 host OS (macOS), 1 user persona (developer)
- 6 firmware modules (per Constitution V), 1 companion daemon
- 4 agent states, 3 display modes, 4 message types
- Reference code strategy: 1 forked repo + 4 reference repos
- Phase 0: 5 POCs over ~7 working days

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. USB Composite Device First | ✅ PASS | Spec Section 1 recommends UAC2 + HID + CDC composite over single USB-C |
| II. Hardware-Native Performance | ✅ PASS | Latency budgets documented (audio <30ms, HID <5ms, display <16ms/frame); heap floor 64KB |
| III. Screen-First UX | ✅ PASS | 3 display modes defined with priority hierarchy; 4 agent states with display behavior per state |
| IV. Reliable Connection | ✅ PASS | Auto re-enumeration <2s; watchdog timer; graceful degradation when serial drops; CDC + HID + Audio independent |
| V. Modular Firmware Architecture | ✅ PASS | 6 modules defined (usb_stack, audio_pipeline, display_ui, host_comm, keyboard, power_mgmt); header-only interfaces; DAG dependency graph |

**Gate Result**: ALL PASS — no violations to justify. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-deep-research-solutions/
├── plan.md              # This file — execution roadmap
├── research.md          # Phase 0 — deep technical research
├── data-model.md        # Phase 1 — protocol schema, state machine, module interfaces
├── quickstart.md        # Phase 1 — developer onboarding guide
├── contracts/           # Phase 1 — interface contracts
│   ├── usb-descriptor.md     # USB composite device descriptor specification
│   ├── host-protocol.md      # Host-to-device JSON protocol (CDC serial)
│   ├── hid-reports.md        # HID keyboard report format and key mapping
│   └── audio-format.md       # UAC2 audio format specification
└── tasks.md             # Phase 2 — /speckit-tasks output (NOT created by this command)
```

### Source Code (future firmware feature spec)

```text
firmware/                      # Fork of lshaf/unigeek, stripped down
├── platformio.ini             # PlatformIO config (Cardputer-Adv env only)
├── src/
│   ├── main.cpp               # Entry point, FreeRTOS task creation
│   ├── usb_stack/             # TinyUSB composite descriptor, UAC2 + HID + CDC
│   │   ├── usb_descriptors.h  # USB descriptor configuration
│   │   ├── uac2_mic.cpp       # UAC2 microphone callbacks + PCM buffer
│   │   └── hid_kbd.cpp        # HID keyboard report dispatch
│   ├── audio_pipeline/        # ES8311 codec init, I2S capture, gain control
│   │   ├── es8311_driver.cpp  # ES8311 init + ADC config (via esp_codec_dev)
│   │   └── i2s_capture.cpp    # I2S RX DMA → PCM ring buffer
│   ├── display_ui/            # Screen rendering, mode switching
│   │   ├── ui_modes.cpp       # Agent status, audio VU, idle modes
│   │   └── render_engine.cpp  # TFT_eSPI drawing primitives
│   ├── host_comm/             # USB CDC serial protocol
│   │   ├── cdc_serial.cpp     # CDC ACM RX/TX, line buffering
│   │   └── protocol.cpp       # JSON parse/serialize, message dispatch
│   ├── keyboard/              # TCA8418RTWR scan, debounce, keymap
│   │   └── keymap.cpp         # Physical key → HID usage code mapping
│   └── power_mgmt/            # Battery ADC, charging state
│       └── battery.cpp        # M5Cardputer.Power wrapper
├── lib/                       # Vendored libraries (from UniGeek)
├── test/                      # Host-side unit tests
│   ├── test_protocol.cpp
│   ├── test_keymap.cpp
│   └── test_ui_modes.cpp
└── tools/                     # Companion daemon + test scripts
    ├── ccb_daemon.py          # Claude Code Buddy Mac daemon
    └── test_sender.py         # Mock agent status sender for testing
```

**Structure Decision**: Single firmware project (PlatformIO + Arduino framework) forked
from lshaf/unigeek, stripped to Cardputer-Adv only, with new modules added for UAC2 mic,
I2S capture, CDC serial, and agent UI. Mac companion daemon is a standalone Python script
in `tools/`. This is documented here for reference; the actual firmware code will be
created under a separate feature spec.

## Complexity Tracking

> No constitution violations. Section left empty per template instructions.

## Execution Roadmap

### Phase 0: Deep Research & Validation (This Feature)

| # | POC | Effort | Depends On | Success Criteria |
|---|-----|--------|------------|------------------|
| P0.1 | UAC2 Mic on UniGeek | 1 day | None | macOS enumerates Audio + HID composite |
| P0.2 | ES8311 Mic Capture | 1 day | None | PCM samples verified via serial dump |
| P0.3 | Audio-to-UAC2 Pipeline | 2 days | P0.1, P0.2 | macOS receives clean 16kHz mono audio |
| P0.4 | CDC Serial + Agent UI | 2 days | P0.1 | JSON frames → display update <200ms |
| P0.5 | UniGeek Strip-Down | 1 day | None | Binary <700KB, all retained features work |

**Phase 0 Deliverable**: Validated technical approach with working proof-of-concept code.

### Phase 1: Firmware Implementation (Future Feature Spec)

| Step | Description | Effort |
|------|-------------|--------|
| 1.1 | Fork & strip UniGeek | 2 days |
| 1.2 | Implement usb_stack module (TinyUSB UAC2+HID+CDC) | 3 days |
| 1.3 | Implement audio_pipeline module (ES8311 mic + I2S RX) | 3 days |
| 1.4 | Implement display_ui module (3 modes + 4 states) | 4 days |
| 1.5 | Implement host_comm module (CDC serial + JSON protocol) | 2 days |
| 1.6 | Implement keyboard module (keymap for MacWhisper trigger) | 1 day |
| 1.7 | Implement power_mgmt module (battery, sleep) | 1 day |
| 1.8 | Integration + end-to-end testing | 3 days |

**Phase 1 Total**: ~19 working days (~4 weeks)

### Phase 2: Mac Companion Daemon (Future Feature Spec)

| Step | Description | Effort |
|------|-------------|--------|
| 2.1 | Claude Code output parser (stdout scraping or API hooks) | 2 days |
| 2.2 | Serial port manager (detect, connect, reconnect) | 1 day |
| 2.3 | JSON protocol encoder + frame dispatch | 1 day |
| 2.4 | System tray / background daemon packaging | 1 day |

**Phase 2 Total**: ~5 working days (~1 week)

### Phase 3: Polish & Hardening (Future)

- BLE secondary channel for wireless status monitoring
- Speaker output for agent voice responses
- Windows/Linux host support
- OTA firmware updates
- Secure boot / flash encryption

### Milestone Summary

```text
Week 1:    Phase 0 POCs — validate USB composite, ES8311 mic, audio-to-UAC2, UI+protocol
Week 2-3:  Decision gate — go/no-go based on POC results
Week 4-7:  Phase 1 — firmware implementation (future feature spec)
Week 8:    Phase 2 — Mac companion daemon (future feature spec)
Week 9+:   Phase 3 — polish, hardening, cross-platform
```

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| TinyUSB UAC2 not compatible with Arduino USB stack in UniGeek | Medium | High — would require switching to pure ESP-IDF | P0.1 validates this first; fallback: fork arduino-esp32 with CFG_TUD_AUDIO=1 |
| ES8311 ADC path not accessible via M5Cardputer.Speaker API (speaker-only) | Medium | Medium — need direct I2S RX config | P0.2 tests low-level I2S; fallback: use esp_codec_dev directly |
| USB bus bandwidth contention (audio + HID + CDC) | Low | Medium — audio glitches or HID lag | USB Full-Speed has 12 Mbps; combined usage <500 kbps; test in P0.3 |
| UniGeek license (GPL-3.0) restrictive for intended use | Low | Low — project is open-source firmware | Our modifications also GPL-3.0; no proprietary distribution planned |
| MacWhisper doesn't recognize external USB mic properly | Low | Medium — users can't use Cardputer as dictation mic | Test in P0.3; macOS should recognize any UAC2 standard mic |

## Dependencies (Cross-Project)

```text
This feature (001-deep-research-solutions)
    │
    ├── Produces: solution options, PRD, execution roadmap
    │
    └── Feeds into: Future feature spec for firmware implementation
                         │
                         ├── /speckit-specify → firmware build spec
                         ├── /speckit-plan → firmware implementation plan
                         └── /speckit-tasks → firmware task breakdown
```
