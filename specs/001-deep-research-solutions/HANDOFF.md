# Implementation Handoff: Cardputer-Adv Claude Code Buddy

**Date**: 2026-06-07
**From**: Research Phase (001-deep-research-solutions)
**To**: Firmware Implementation Phase

## What's Decided

All major technical decisions are made and documented:
- **USB Stack**: TinyUSB (Espressif fork) with CFG_TUD_AUDIO=1
- **Base Firmware**: Fork lshaf/unigeek, strip to Cardputer-Adv only
- **Audio**: ES8311 via esp_codec_dev + direct I2S RX DMA (GPIO46)
- **Display**: TFT_eSPI, framebuffer-less, 3 modes + 4 states
- **Protocol**: USB CDC serial, newline-delimited JSON, 4 message types
- **Host**: Python daemon, subprocess stdout scraping, <200 lines

## What's POC-Validated (via Code Analysis)

These decisions are supported by deep codebase analysis but NOT yet hardware-validated:

| Decision | Confidence | Validation Method |
|----------|------------|-------------------|
| TinyUSB UAC2 on ESP32-S3 | High | atomic14 reference code + TinyUSB docs |
| ES8311 ADC capture | High | Datasheet register map + esp_codec_dev source |
| UniGeek strip-down feasibility | High | Full codebase analysis + feature isolation |
| TFT_eSPI on Cardputer-Adv | High | UniGeek already uses this exact config |
| JSON protocol viability | High | Claude Desktop Buddy uses same pattern |

## What Still Needs Validation (Hardware Required)

### Gate 1: USB Enumeration (CRITICAL)
- Flash `poc/usb-composite/` to Cardputer-Adv
- Command: `system_profiler SPUSBDataType | grep -A 15 Cardputer`
- **Go**: UAC2 + HID + CDC all appear
- **No-Go**: Only some interfaces appear → debug TinyUSB descriptor or try ESP-IDF

### Gate 2: ES8311 Mic Capture
- Flash `poc/es8311-capture/` (combined with USB POC)
- Open System Settings → Sound → Input → speak → watch level meter
- Record in QuickTime → listen for clean audio
- **Go**: Clean 16kHz audio, level meter moves
- **No-Go**: No audio → check I2C bus, verify ES8311 at 0x18, try direct reg writes

### Gate 3: Display UI
- Flash `poc/display-ui/` with mock data
- Verify: all 3 modes render, >15 FPS, heap >64KB
- **Go**: Screen works, text readable
- **No-Go**: Flickering/crashing → check SPI freq, verify TFT_eSPI config

### Gate 4: Host Protocol
- Run `python tools/test_sender.py` after flashing `poc/host-comm/`
- Verify: screen updates within 200ms, 1000 messages no drops, disconnect shows error
- **Go**: Protocol reliable
- **No-Go**: Dropped frames → check CDC buffer sizes, increase to 512

### Gate 5: UniGeek Strip-Down
- Build stripped UniGeek: `pio run -e m5_cardputer_adv`
- Verify binary <700KB
- **Go**: Stripped + integrated firmware builds and flashes
- **No-Go**: Binary too large → strip more aggressively or optimize

## Reference Code Pointers

| Need | Source File |
|------|-------------|
| UAC2 descriptor template | `poc/uac-reference/serial-mic/src/` (atomic14) |
| UAC2 callbacks | `poc/usb-composite/src/usb_descriptors.c` (our code) |
| ES8311 init sequence | `poc/es8311-capture/src/es8311_init.cpp` (our code) |
| I2S RX config | `poc/es8311-capture/src/i2s_capture.cpp` (our code) |
| PCM ring buffer | `poc/es8311-capture/src/ring_buffer.h` (our code) |
| Display mode manager | `poc/display-ui/src/ui_mode_manager.cpp` (our code) |
| JSON protocol parser | `poc/host-comm/src/protocol_parser.cpp` (our code) |
| Python test sender | `tools/test_sender.py` (our code) |
| UniGeek keyboard driver | `poc/unigeek-base/firmware/boards/m5_cardputer_adv/core/Keyboard.h` |
| UniGeek ES8311 speaker | `poc/unigeek-base/firmware/boards/m5_cardputer_adv/core/Speaker.h` |
| UniGeek display config | `poc/unigeek-base/firmware/boards/m5_cardputer_adv/pins_arduino.h` |

## Known Issues & Gotchas

1. **I2C bus sharing**: TCA8418 (0x34), ES8311 (0x18), BMI270 (0x68) all on Wire1.
   Thread-safe access required — use mutex or ensure single-threaded I2C usage.

2. **I2S port conflict**: UniGeek uses I2S_NUM_1 for speaker. For mic capture, use
   I2S_NUM_0 for RX or configure I2S_NUM_1 in full-duplex mode.

3. **Arduino USB vs TinyUSB**: Switching from `ARDUINO_USB_MODE=1` to TinyUSB breaks
   Arduino's `Serial` (HW CDC). Replace all `Serial.print` with TinyUSB CDC or UART0.

4. **ADC2 limitation**: ESP32-S3 ADC2 is shared with Wi-Fi. Since v1 is USB-only
   (no Wi-Fi), this is not an issue. For future Wi-Fi + audio, use ADC1 only.

5. **ES8311 clock**: MCLK must be correctly configured for 16kHz. The formula is:
   MCLK = 256 × Fs × MULT_PRE = 256 × 16000 × 3 = 12.288 MHz (unusual).
   Alternative: use 4.096 MHz MCLK with MULT_PRE=1 and appropriate dividers.

6. **TFT_eSPI rotation**: Cardputer-Adv display is 240×135 with TFT_WIDTH=135 and
   TFT_HEIGHT=240 (portrait rotated). This is already configured in UniGeek's
   pins_arduino.h (`TFT_DEFAULT_ORIENTATION 1`).

## Quick-Start for Implementation

```bash
# 1. Clone our repo
git clone https://github.com/harv-dragon/cardputer-adv-claude-code-buddy.git
cd cardputer-adv-claude-code-buddy

# 2. Build the POC firmware
cd poc/usb-composite
pio run -e cardputer-adv-usb-poc
pio run -e cardputer-adv-usb-poc -t upload

# 3. Verify USB enumeration
system_profiler SPUSBDataType | grep -A 15 Cardputer

# 4. Run test sender
cd ../..
python tools/test_sender.py

# 5. If all POCs pass, proceed to firmware/ fork and strip-down
# Follow poc/unigeek-base/STRIPDOWN_PLAN.md
```

## File Index

| Document | Path | Purpose |
|----------|------|---------|
| Spec | `specs/001-deep-research-solutions/spec.md` | Feature spec with user stories & solution options |
| Plan | `specs/001-deep-research-solutions/plan.md` | Implementation plan + execution roadmap |
| Research | `specs/001-deep-research-solutions/research.md` | Deep technical decisions (6 topics, 10 decisions) |
| Data Model | `specs/001-deep-research-solutions/data-model.md` | Entities, state machine, FreeRTOS tasks |
| PRD | `specs/001-deep-research-solutions/PRD.md` | Product requirements document |
| BOM | `specs/001-deep-research-solutions/BOM.md` | Bill of materials (hardware + software) |
| Summary | `specs/001-deep-research-solutions/SUMMARY.md` | Executive summary |
| Contracts | `specs/001-deep-research-solutions/contracts/` | USB, HID, audio, protocol contracts |
| Tasks | `specs/001-deep-research-solutions/tasks.md` | 74-task breakdown |
| Quickstart | `specs/001-deep-research-solutions/quickstart.md` | Developer onboarding |
| This file | `specs/001-deep-research-solutions/HANDOFF.md` | Implementation handoff |
