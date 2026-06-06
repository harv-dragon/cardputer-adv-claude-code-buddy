# Product Requirements Document: Cardputer-Adv Claude Code Buddy

**Version**: 1.0.0 | **Date**: 2026-06-07 | **Status**: Draft
**Feature**: 001-deep-research-solutions

## Executive Summary

The Cardputer-Adv Claude Code Buddy is a firmware + companion daemon that turns the
M5Stack Cardputer-Adv into a **USB composite device (microphone + keyboard)** for
voice-driven AI coding. The user holds the Cardputer to their mouth, presses a key to
trigger MacWhisper dictation, and speaks coding instructions. The Cardputer screen
displays real-time CLI agent status from Claude Code running on the Mac.

## Problem Statement

Developers using CLI AI coding agents (Claude Code, etc.) face two friction points:
1. **Voice input requires switching to the Mac's built-in mic** — losing the close-talk
   audio quality needed for accurate transcription in noisy environments.
2. **Agent status is invisible when the terminal is buried** — developers constantly
   alt-tab to check if the agent is done, waiting for permission, or errored.

The Cardputer-Adv solves both: it's a handheld USB mic (better voice quality via
close-talk) with a keyboard shortcut trigger and a dedicated status display.

## User Personas

### Primary: AI-Assisted Developer
- Uses Claude Code or similar CLI agent daily
- Prefers voice dictation for long instructions (reduces typing fatigue)
- Works in various environments (office, home, coffee shop)
- Has an Apple Silicon MacBook with MacWhisper

### Secondary: Firmware Hacker
- Owns a Cardputer-Adv
- Wants to customize the firmware (add features, change UI)
- Comfortable with PlatformIO and C++

## Product Overview

```
┌─────────────────────┐          USB-C           ┌──────────────────────┐
│   Cardputer-Adv     │◄════════════════════════►│    MacBook (macOS)    │
│                     │                          │                      │
│  [MEMS Mic] ──► UAC2 Audio ──────────► MacWhisper ──► transcribed text│
│  [Keyboard] ──► HID Keycode ──────────► MacWhisper trigger            │
│  [Display]  ◄── CDC Serial ◄────────── Claude Code agent status      │
│                     │                          │                      │
└─────────────────────┘                          └──────────────────────┘
```

## Functional Requirements

### FR1: USB Composite Device
- **FR1.1**: Device enumerates as USB composite with UAC2 Audio (microphone) + HID Keyboard + CDC ACM (serial)
- **FR1.2**: No custom drivers required — uses macOS built-in class drivers
- **FR1.3**: Full enumeration in <3 seconds after USB connection
- **FR1.4**: Survives cable disconnect/reconnect without device reset

### FR2: Microphone Capture
- **FR2.1**: Captures audio from MEMS mic via ES8311 ADC at 16-bit 16kHz mono
- **FR2.2**: End-to-end latency <30ms (mic membrane → USB UAC2 endpoint)
- **FR2.3**: Zero dropped samples in 10 minutes of continuous streaming
- **FR2.4**: SNR within 5dB of MacBook built-in mic

### FR3: HID Keyboard
- **FR3.1**: Cardputer QWERTY keys map to standard USB HID keyboard usage codes
- **FR3.2**: Dictation trigger key (default: hold SPACE → Right Command) configurable via NVS
- **FR3.3**: Key reports delivered within 5ms of physical keypress
- **FR3.4**: 6KRO (6-key rollover) with modifier support

### FR4: Display UI
- **FR4.1**: Three display modes: Agent Status, Audio VU, Idle
- **FR4.2**: Four agent states: idle, running, waiting_permission, error
- **FR4.3**: Mode priority: waiting_permission > error > running > audio_input > idle
- **FR4.4**: Minimum 15 FPS for text updates, 30 FPS for VU meter animation
- **FR4.5**: At least 64KB free heap at all times

### FR5: Host Communication
- **FR5.1**: USB CDC serial JSON protocol for agent status relay
- **FR5.2**: Four message types: status, permission, log, config
- **FR5.3**: Monotonic sequence numbering with dropped frame detection
- **FR5.4**: Host disconnect detection with 5-second timeout
- **FR5.5**: End-to-end latency <200ms from Mac daemon send to screen render

### FR6: Mac Companion Daemon
- **FR6.1**: Python script that monitors Claude Code output and forwards status to Cardputer
- **FR6.2**: Auto-detects Cardputer CDC serial port
- **FR6.3**: Handles Claude Code session start/stop, token counting, command tracking
- **FR6.4**: <200 lines of code, zero external dependencies beyond Python stdlib + pyserial

### FR7: Power Management
- **FR7.1**: Battery percentage display on idle screen (ADC via analogReadMilliVolts)
- **FR7.2**: USB-powered operation is primary use case (charging while operating)
- **FR7.3**: Screen dim after configurable idle timeout (default 5 min)

## Non-Functional Requirements

### Performance
| Metric | Target | Verification |
|--------|--------|-------------|
| Audio latency | <30ms | Tap test in Audacity |
| USB enumeration | <3s | `system_profiler` timing |
| Display FPS (text) | ≥15 FPS | Frame counter |
| Display FPS (VU) | ≥30 FPS | Frame counter |
| HID key latency | <5ms | High-speed camera / oscilloscope |
| Protocol latency | <200ms | Python timestamp delta |
| Free heap | ≥64KB | `esp_get_free_heap_size()` |

### Reliability
- USB re-enumeration after disconnect: <2 seconds
- Watchdog timer: 5-second timeout
- Audio streaming: 0 dropped samples in 10 minutes
- Protocol: 0 dropped frames in 1000 rapid messages

### Compatibility
- macOS 15 Sequoia (Apple Silicon) — primary target
- macOS 14 Sonoma — secondary (untested, should work)
- Windows/Linux — v2 (USB standards-compliant descriptors)

### Memory
- Binary size: <1MB (fits within 4MB firmware partition with 2MB SPIFFS)
- RAM: 64KB free heap minimum (no PSRAM on ESP32-S3FN8)

## Technical Architecture

### Firmware Stack
```text
Application:   display_ui, host_comm, keyboard, power_mgmt
Middleware:    TinyUSB (UAC2+HID+CDC), ArduinoJson, TFT_eSPI
Drivers:       ES8311 (I2S+I2C), ST7789V2 (SPI), TCA8418 (I2C)
HAL:           M5Cardputer, M5Unified
RTOS:          FreeRTOS (dual-core)
Board:         ESP32-S3FN8 (Cardputer-Adv)
```

### Module Architecture (Constitution V)
| Module | Responsibility |
|--------|---------------|
| usb_stack | TinyUSB composite device descriptor, UAC2+HID+CDC endpoints |
| audio_pipeline | ES8311 codec init, I2S capture, gain control, mute |
| display_ui | Screen rendering, mode switching, TFT_eSPI drawing |
| host_comm | USB CDC serial protocol for agent status, JSON parsing |
| keyboard | TCA8418RTWR scan, debounce, keymap, macro keys |
| power_mgmt | Battery ADC, charging state, sleep/wake policy |

### Host Stack
```text
Claude Code (terminal) → ccb_daemon.py (Python) → CDC Serial (/dev/tty.usbmodem*)
```

### Data Flow
```text
[Mic] → ES8311 ADC → I2S RX DMA → Ring Buffer → UAC2 TX Callback → USB → macOS → MacWhisper
[Key] → TCA8418 → KeyboardImpl::update() → HID Report → USB → macOS → MacWhisper shortcut
[Agent] → Claude Code stdout → ccb_daemon.py → JSON frame → USB CDC → protocol_parser → display_ui
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Voice-to-code latency | <2 seconds from end of speech to text in editor |
| Transcription accuracy | >95% (same as MacBook built-in mic) |
| USB plug-and-play | Works on first plug, zero configuration |
| Battery life | >2 hours continuous dictation + display |
| Developer setup time | <30 minutes from clone to flash |

## Out of Scope (v1)

- On-device speech recognition or Whisper inference
- BLE or Wi-Fi communication (USB-only)
- Audio output / speaker playback
- Windows or Linux host support
- OTA firmware updates
- Secure boot / flash encryption
- Multi-device support

## Dependencies

### Hardware
- M5Stack Cardputer-Adv (SKU: K132-Adv, ESP32-S3FN8)

### Software (Firmware)
- PlatformIO + Arduino framework (espressif32@6.13.0)
- TinyUSB (Espressif fork, CFG_TUD_AUDIO=1 enabled)
- TFT_eSPI, ArduinoJson v7, M5Cardputer, M5Unified

### Software (Host)
- macOS 15+ (Apple Silicon)
- MacWhisper (or equivalent) with keyboard shortcut trigger
- Python 3.11+ with pyserial

### Base Repository
- [lshaf/unigeek](https://github.com/lshaf/unigeek) (GPL-3.0) — forked and stripped

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| TinyUSB UAC2 incompatible with Arduino framework | Medium | High | P0.1 POC validates; fallback to ESP-IDF |
| ES8311 ADC path not accessible via M5Cardputer API | Medium | Medium | Direct I2S RX + esp_codec_dev |
| USB bandwidth contention | Low | Medium | Combined <500 kbps on 12 Mbps bus |
| GPL-3.0 license restrictions | Low | Low | Project also GPL-3.0 |
