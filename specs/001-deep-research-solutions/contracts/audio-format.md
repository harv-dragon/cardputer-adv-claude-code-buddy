# UAC2 Audio Format Specification

**Feature**: 001-deep-research-solutions
**Contract Type**: Audio Format Contract (USB Audio Class 2.0)
**Version**: 1.0.0

## Audio Format

| Parameter | Value | Notes |
|-----------|-------|-------|
| Format | PCM (Linear) | UAC2 FORMAT_TYPE_I |
| Sample Rate | 16000 Hz | Voice-optimized; sufficient for Whisper STT |
| Bit Depth | 16-bit signed integer | Little-endian |
| Channels | 1 (Mono) | |
| Byte Rate | 32000 bytes/sec | 16000 samples × 2 bytes |
| USB Endpoint | Isochronous IN, adaptive | 1ms interval (1 packet per USB microframe) |
| Packet Size | 32 bytes | 16 samples × 2 bytes per 1ms packet |
| Clock Source | Internal fixed clock | ESP32-S3 internal oscillator |
| Input Terminal | Microphone (0x0201) | USB Audio Class terminal type |

## Supported Alternate Sample Rates

The UAC2 descriptor advertises the following sample rates via a class-specific
clock source frequency range. The default is 16000 Hz.

| Sample Rate | Bytes/ms | Packet Size | Use Case |
|-------------|----------|-------------|----------|
| 8000 Hz | 16 | 16 bytes | Low bandwidth, telephony quality |
| 16000 Hz | 32 | 32 bytes | **Default** — optimized for voice recognition |
| 22050 Hz | ~44 | 44 bytes | Higher quality voice |
| 44100 Hz | ~88 | 88 bytes | CD quality (requires 2 packets/ms or larger packets) |
| 48000 Hz | 96 | 96 bytes | Pro audio (requires 2 packets/ms or larger packets) |

> **Note**: 44100 Hz and 48000 Hz may exceed USB Full-Speed isochronous endpoint
> bandwidth limits for a single microframe (max 1023 bytes). Use only if the
> ESP32-S3 USB peripheral supports High-Speed (unlikely) or if the host supports
> packet splitting. **For v1, only 8000-16000 Hz are actively tested.**

## Audio Pipeline

```text
MEMS Mic → ES8311 ADC → I2S RX (GPIO46) → DMA Buffer → Ring Buffer → UAC2 TX Callback → USB Isochronous IN
                                                         ↑
                                                   (CPU: Ring buffer read/write pointers)
```

### Latency Budget

| Stage | Latency | Notes |
|-------|---------|-------|
| Acoustic (mouth → mic) | ~0.3ms | Speed of sound @ 10cm distance |
| ES8311 ADC conversion | ~0.5ms | 24-bit sigma-delta ADC |
| I2S serial transfer | ~0.06ms | 16 bits × 16000 Hz / 2.4 Mbps I2S clock |
| DMA buffer (256 samples) | 16ms | 4 DMA descriptors × 256 frames each |
| Ring buffer (1024 samples) | 0-16ms | Depends on read/write pointer offset |
| UAC2 TX preparation | ~0.5ms | Callback execution + memcpy to USB buffer |
| USB isochronous transfer | 1ms | 1 microframe (125μs) × 8 = worst case |
| macOS USB stack → Audio HAL | ~2ms | Kernel → userspace → CoreAudio |
| **Total (worst case)** | **~36ms** | Exceeds 30ms target in worst case |

**Optimizations to meet 30ms target**:
- Reduce DMA buffer size to 128 samples (8ms) → saves 4ms
- Reduce ring buffer size to 512 samples → saves 8ms
- Tune UAC2 callback timing to minimize ring buffer fullness → saves 4ms
- **Optimized total**: ~20ms ✅

### Audio Quality Targets

| Metric | Target | Notes |
|--------|--------|-------|
| SNR (Signal-to-Noise Ratio) | ≥60 dB (A-weighted) | ES8311 ADC SNR spec is 100 dB; MEMS mic SNR is 65 dB |
| THD+N | ≤0.1% at 1kHz, -20dBFS | |
| Frequency Response | 100 Hz - 7.5 kHz (-3dB) | Voice band; Nyquist limit at 8 kHz with 16 kHz sample rate |
| Sample Drop Rate | 0 samples dropped in 10 minutes | |
| USB Buffer Underrun Rate | 0 underruns in 10 minutes | |

## ES8311 ADC Configuration

The ES8311 ADC is configured for voice capture:

| Register/Setting | Value | Description |
|-----------------|-------|-------------|
| ADC Sample Rate | 16000 Hz | Via clock divider from MCLK |
| ADC Bit Depth | 16-bit | I2S standard Philips format |
| PGA Gain | +30 dB | Mic preamplifier — suitable for close-talk (mouth-to-device) |
| Mic Bias | Enabled, 2.0V | MEMS mic power |
| ADC High-Pass Filter | Enabled, cutoff @ 100 Hz | Remove low-frequency rumble |
| ADC Low-Pass Filter | Enabled, cutoff @ 7.5 kHz | Anti-aliasing for 16 kHz sample rate |
| ADC Mute | Disabled (unmuted) | Active capture |

## I2S Configuration (ESP32-S3 RX)

```c
i2s_port_t:       I2S_NUM_1 (RX only)
i2s_mode:         I2S_MODE_MASTER | I2S_MODE_RX
i2s_sample_rate:  16000 Hz
i2s_bits:         I2S_BITS_PER_SAMPLE_16BIT
i2s_format:       I2S_COMM_FORMAT_STAND_PHILIPS
i2s_channel:      I2S_CHANNEL_FMT_ONLY_LEFT (MONO)

GPIO:
  mck:  I2S_GPIO_UNUSED  (ES8311 generates MCLK internally)
  bck:  GPIO_NUM_41      (I2S bit clock)
  ws:   GPIO_NUM_43      (I2S word select / LRCK)
  din:  GPIO_NUM_46      (I2S data IN from ES8311 ASDOUT)
  dout: I2S_GPIO_UNUSED  (no speaker output in mic mode)

DMA:
  dma_buf_count:  4
  dma_buf_len:    256  (128 samples per buffer, 8ms each)
```

## macOS Audio Compatibility

- macOS recognizes UAC2 microphone input natively (no driver needed, macOS 10.6+).
- Device appears in System Settings → Sound → Input as "Cardputer-Adv".
- CoreAudio will request the streaming interface with Alt Setting 1 when an app opens
  the microphone (e.g., MacWhisper starts listening).
- When no app is using the mic, CoreAudio will set Alt Setting 0 (zero bandwidth).
  The firmware MUST stop I2S capture and UAC2 streaming when Alt 0 is selected to
  conserve power.

## Firmware Callback Contract

The TinyUSB UAC2 callback fires at the USB frame rate (1 kHz = every 1ms):

```c
// Called every 1ms when streaming is active (Alt Setting 1)
void tud_audio_tx_done_pre_load_cb(uint8_t rhport,
    uint8_t itf, uint8_t ep_in, uint8_t cur_alt_setting)
{
    // Read 16 samples (32 bytes) from ring buffer
    // Write to TinyUSB FIFO via tud_audio_n_write()
    // Return number of bytes written
}
```

**Requirements**:
- Callback MUST NOT block (no mutex wait, no I2C transaction)
- Callback MUST complete in <100μs (USB interrupt context)
- Ring buffer access MUST use lock-free atomic operations
- If ring buffer has <16 samples available, send silence (zero-fill) to avoid underrun
