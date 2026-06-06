# Bill of Materials & Dependencies

**Feature**: 001-deep-research-solutions
**Date**: 2026-06-07

## Hardware

| Item | SKU/Model | Qty | Purpose |
|------|-----------|-----|---------|
| M5Stack Cardputer-Adv | K132-Adv | 1 | Target device |
| USB-C cable (data) | — | 1 | Power + data to Mac |
| Mac (Apple Silicon) | M1+ | 1 | Development + host |

## Firmware Dependencies (PlatformIO)

| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| espressif32 (platform) | 6.13.0 | Apache-2.0 | Build platform |
| Arduino framework | 2.0.17 | LGPL-2.1 | Base framework |
| TFT_eSPI (Bodmer) | ^2.5.43 | MIT | Display driver |
| ArduinoJson (bblanchon) | ^7.0.0 | MIT | JSON protocol parser |
| M5Cardputer | ^1.1.1 | MIT | Hardware abstraction |
| M5Unified | ^0.2.10 | MIT | Unified HW API |
| Adafruit TCA8418 | ^1.0.0 | BSD-3 | Keyboard I/O expander |
| TJpg_Decoder (Bodmer) | ^1.1.0 | MIT | Image support (optional) |

### TinyUSB Build Flags

```ini
-DARDUINO_USB_MODE=0
-DUSE_TINYUSB=1
-DCFG_TUD_AUDIO=1
-DCFG_TUD_AUDIO_FUNC_1_N_BYTES_SAMPLE=2
-DCFG_TUD_AUDIO_FUNC_1_SAMPLE_RATE=16000
-DCFG_TUD_HID=1
-DCFG_TUD_HID_BOOT=1
-DCFG_TUD_CDC=1
```

## Host Dependencies (Python)

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| Python | 3.11+ | PSF | Runtime |
| pyserial | 3.5+ | BSD-3 | Serial port communication |

## Reference Repositories (Code Patterns)

| Repository | URL | Commit (if pinned) | Usage |
|------------|-----|-------------------|-------|
| lshaf/unigeek | https://github.com/lshaf/unigeek | master (2026-06-06) | Base firmware fork |
| atomic14/esp32-usb-uac-experiments | https://github.com/atomic14/esp32-usb-uac-experiments | master (2026-06-06) | UAC2 descriptor + callback patterns |
| anthropics/claude-desktop-buddy | https://github.com/anthropics/claude-desktop-buddy | main (2026-06-06) | State machine + protocol schema |

## Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| PlatformIO CLI | latest | Build + flash |
| esptool.py | 4.x | Flashing |
| Python | 3.11+ | Test scripts + daemon |
| Git | 2.x | Version control |
| GitHub CLI (gh) | 2.93+ | Repository management |
| MacWhisper | latest | Voice-to-text host software |

## macOS Software (Runtime)

| Software | Version | Purpose |
|----------|---------|---------|
| macOS | 15 Sequoia | Host OS |
| MacWhisper | latest | Voice-to-text dictation |
| Claude Code | latest | CLI AI coding agent |
| Python | 3.11+ | Companion daemon runtime |
