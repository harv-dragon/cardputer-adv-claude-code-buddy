# Quickstart: Cardputer-Adv Claude Code Buddy Firmware

**Feature**: 001-deep-research-solutions
**Created**: 2026-06-06

## Prerequisites

### Hardware
- M5Stack Cardputer-Adv (SKU: K132-Adv)
- USB-C cable (data-capable, not charge-only)
- Mac with Apple Silicon (M1+) running macOS 15 Sequoia+
- MacWhisper installed and configured with Right Command or Right Option as dictation key

### Software (Development Machine)
- PlatformIO (install via `brew install platformio` or VS Code extension)
- ESP32-S3 USB driver (if not already installed: <https://docs.m5stack.com/en/guide/faq/driver>)
- Python 3.11+ (for companion daemon)
- pyserial (`pip install pyserial`)

## Phase 0: Proof-of-Concept Setup

### Step 1: Clone Base Repository

```bash
# Clone UniGeek as the starting point
git clone https://github.com/lshaf/unigeek.git
cd unigeek

# Create a branch for our modifications
git checkout -b cardputer-adv-claude-buddy
```

### Step 2: Configure PlatformIO for Cardputer-Adv + TinyUSB

```bash
# Edit platformio.ini — set up Cardputer-Adv environment with TinyUSB
```

Key `platformio.ini` settings:

```ini
[env:cardputer-adv-ccb]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
upload_speed = 1500000

build_flags =
    -DESP32S3
    -DCORE_DEBUG_LEVEL=0
    -DARDUINO_USB_MODE=0          # Disable Arduino USB stack
    -DUSE_TINYUSB=1               # Enable TinyUSB
    -DCFG_TUD_AUDIO=1             # Enable UAC2
    -DCFG_TUD_AUDIO_FUNC_1_N_BYTES_SAMPLE=2   # 16-bit
    -DCFG_TUD_AUDIO_FUNC_1_SAMPLE_RATE=16000   # 16kHz
    -DCFG_TUD_CDC=1               # Enable CDC serial

lib_deps =
    m5stack/M5Cardputer @ ^1.1.1
    m5stack/M5Unified @ ^0.2.10
    bodmer/TFT_eSPI @ ^2.5.0
    bblanchon/ArduinoJson @ ^7.0.0
```

### Step 3: Flash Factory Test

```bash
# Build and flash
pio run -e cardputer-adv-ccb -t upload

# Monitor serial for debug output
pio device monitor -b 115200
```

### Step 4: Verify USB Enumeration

```bash
# Check macOS sees the device
system_profiler SPUSBDataType | grep -A 15 "Cardputer-Adv"

# Expected: Vendor 0x303A, three interfaces (Audio, HID, CDC)
```

### Step 5: Test Audio

```bash
# Check if macOS sees the microphone
system_profiler SPAudioDataType | grep -A 5 "Cardputer-Adv"

# Open System Settings → Sound → Input
# Speak into Cardputer → verify level meter moves
```

### Step 6: Test Keyboard

```bash
# Open any text editor
# Press keys on Cardputer → verify characters appear
# Press and hold SPACE → verify Right Command triggers MacWhisper
```

### Step 7: Run Companion Daemon (Mock)

```bash
# Install test dependencies
pip install pyserial

# Run the mock sender (sends fake agent status for UI testing)
python tools/test_sender.py --port /dev/tty.usbmodem*

# Cardputer screen should show mock agent status with runtime counter,
# token count, and fake command entries
```

## Phase 1: Full Firmware Build

After Phase 0 POCs validate the approach:

```bash
# 1. Fork & strip UniGeek (remove unused features)
#    See plan.md "UniGeek Features to Remove" list

# 2. Add new modules
#    - src/usb_stack/     (TinyUSB UAC2+HID+CDC descriptors)
#    - src/audio_pipeline/ (ES8311 ADC + I2S RX DMA)
#    - src/display_ui/    (3 modes + 4 states)
#    - src/host_comm/     (CDC serial + JSON protocol)

# 3. Build
pio run -e cardputer-adv-ccb

# 4. Flash
pio run -e cardputer-adv-ccb -t upload

# 5. Test full workflow:
#    a. Plug in Cardputer-Adv
#    b. Verify Sound → Input shows Cardputer-Adv mic
#    c. Press SPACE → verify MacWhisper activates
#    d. Speak into Cardputer → verify transcription appears
#    e. Run ccb_daemon.py → verify screen shows agent status
```

## Companion Daemon Quickstart

```bash
# Clone the daemon
cd tools/

# Install dependency
pip install pyserial

# Run the daemon (starts Claude Code and forwards status)
python ccb_daemon.py

# Or run with explicit port
python ccb_daemon.py --port /dev/tty.usbmodemCCB-3C6105

# Or run in test mode (mock agent status, no Claude Code needed)
python ccb_daemon.py --mock
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Device not appearing in USB | USB-C cable supports data? Try a different cable. |
| Audio device not showing | Run `system_profiler SPUSBDataType` to confirm Audio interface enumerated. Check Alt Setting in USB descriptors. |
| Keyboard not working | Verify HID descriptor is valid. Check `pio device monitor` for HID init logs. |
| CDC serial port not found | Check `/dev/tty.*` — should see `/dev/tty.usbmodem*`. Verify CDC descriptors. |
| No audio signal | Check ES8311 I2C communication (address 0x18). Verify I2S GPIO config. Check ADC power-up sequence. |
| Display flickering | Check SPI frequency (40MHz max for ST7789V2). Verify backlight PWM on GPIO38. |
| ES8311 init fails | Verify I2C pull-up resistors. Check ES8311 is powered. Try direct register-based init. |
| Low audio volume | Increase PGA gain (range 0-42 dB). Verify mic bias is enabled. |
| USB enumeration slow | Check USB D+ pull-up. Verify TinyUSB task priority. Reduce descriptor complexity. |
