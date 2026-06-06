# Executive Summary: Cardputer-Adv Claude Code Buddy

**Date**: 2026-06-07 | **Status**: Research Complete, Ready for Implementation

## One-Page Summary

The Cardputer-Adv Claude Code Buddy transforms an M5Stack Cardputer-Adv (ESP32-S3,
~$30) into a **USB composite device** that combines a microphone, keyboard, and
status display for voice-driven AI coding with Claude Code on macOS.

### The Architecture

```
Cardputer-Adv ←──USB-C──→ MacBook
   │                         │
   ├─ MEMS Mic → UAC2 ──→ MacWhisper → transcribed text in editor
   ├─ Keyboard → HID ───→ MacWhisper trigger (Right Command)
   └─ Display ← CDC ──── Claude Code status + tokens
```

### Key Decisions (10 total, all POC-validated where possible)

| # | Decision | Choice | Confidence |
|---|----------|--------|------------|
| 1 | USB Stack | TinyUSB (Espressif fork) with UAC2+HID+CDC | High |
| 2 | Base Firmware | Fork lshaf/unigeek, strip to Cardputer-Adv only | High |
| 3 | Audio Driver | esp_codec_dev for ES8311 init + direct I2S DMA | High |
| 4 | Display UI | TFT_eSPI framebuffer-less rendering | High |
| 5 | Host Protocol | USB CDC serial + JSON, newline-delimited | High |
| 6 | Agent States | 4 states: idle, running, waiting_permission, error | High |
| 7 | Mac Daemon | Python, <200 lines, subprocess stdout scraping | Medium |
| 8 | UAC2 Descriptors | Based on atomic14/esp32-usb-uac-experiments code | High |
| 9 | Build System | PlatformIO + Arduino framework (UniGeek base) | High |
| 10 | v2 Migration | Pure ESP-IDF for production hardening | Low (deferred) |

### What's Ready

- **>2,000 lines of POC firmware code** (USB descriptors, ES8311 init, I2S capture,
  ring buffer, UAC2 callbacks, display mode manager, JSON protocol parser)
- **Python test sender** (mock agent simulation, serial auto-detection, burst mode)
- **Complete spec + plan + research** (spec.md, plan.md, research.md, data-model.md,
  4 interface contracts, 74-task breakdown)
- **PRD + BOM** for implementation handoff
- **6 analysis documents** from UniGeek codebase deep-dive

### What Needs Hardware

The POC code is written and ready for a physical Cardputer-Adv. The 5 validation gates:
1. **USB Enumeration POC** — flash `poc/usb-composite/`, verify macOS sees UAC2+HID+CDC
2. **ES8311 Mic Capture** — verify I2S RX from GPIO46 produces valid PCM
3. **Audio-to-USB** — verify macOS receives clean 16kHz audio
4. **Display + Protocol** — verify test_sender.py → screen renders agent status
5. **UniGeek Strip-Down** — verify binary <700KB after removing unused features

### Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0 POCs | 1 week (needs hardware) | Validated USB + Audio + UI + Protocol |
| Phase 1 Firmware | 4 weeks | Working firmware on Cardputer-Adv |
| Phase 2 Daemon | 1 week | Mac companion daemon |
| Phase 3 Polish | 2 weeks | Cross-platform, OTA, hardening |
| **Total to v1 MVP** | **~6 weeks** | |

### Launch-Ready Deliverables

1. PlatformIO firmware (`pio run -e cardputer-adv-ccb -t upload`)
2. Mac companion daemon (`python ccb_daemon.py`)
3. Quickstart guide (quickstart.md)
4. All source under GPL-3.0 at [github.com/harv-dragon/cardputer-adv-claude-code-buddy](https://github.com/harv-dragon/cardputer-adv-claude-code-buddy)
