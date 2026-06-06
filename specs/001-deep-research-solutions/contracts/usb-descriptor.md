# USB Composite Device Descriptor Specification

**Feature**: 001-deep-research-solutions
**Contract Type**: USB Device Descriptor (Hardware Interface)
**Version**: 1.0.0

## Overview

This document specifies the USB composite device descriptor for the Cardputer-Adv firmware.
The device presents as a single USB composite device with three interfaces: UAC2 Audio
(microphone), HID Keyboard, and CDC ACM (virtual serial port).

## Device Descriptor

| Field | Value | Description |
|-------|-------|-------------|
| bLength | 18 | Descriptor size in bytes |
| bDescriptorType | 0x01 | DEVICE |
| bcdUSB | 0x0200 | USB 2.0 |
| bDeviceClass | 0xEF | Miscellaneous (Multi-Interface Function) |
| bDeviceSubClass | 0x02 | Common Class |
| bDeviceProtocol | 0x01 | Interface Association Descriptor |
| bMaxPacketSize0 | 64 | EP0 max packet size |
| idVendor | 0x303A | Espressif (M5Stack default) |
| idProduct | 0x4001 | Custom PID for Cardputer-Adv firmware |
| bcdDevice | 0x0100 | Device release 1.0.0 |
| iManufacturer | "M5Stack" | String index 1 |
| iProduct | "Cardputer-Adv" | String index 2 (configurable via NVS) |
| iSerialNumber | Unique per device | String index 3 (ESP32-S3 MAC-derived) |
| bNumConfigurations | 1 | One configuration |

## Configuration Descriptor

```text
Configuration Descriptor (9 bytes)
  bLength=9, bDescriptorType=0x02 (CONFIGURATION)
  wTotalLength = (calculated)  ← total size including all interfaces
  bNumInterfaces = 3           ← Audio Control + Audio Streaming + HID + CDC
  bConfigurationValue = 1
  iConfiguration = 0 (no string)
  bmAttributes = 0xC0 (Self-powered, no remote wakeup)
  bMaxPower = 100 (200mA)      ← 100 * 2mA units
```

## Interface 0: UAC2 Audio Control

```text
Interface Association Descriptor (8 bytes) ← groups IF 0-2
  bLength=8, bDescriptorType=0x0B
  bFirstInterface=0
  bInterfaceCount=3
  bFunctionClass=0x01 (AUDIO)
  bFunctionSubClass=0x00 (UNDEFINED)
  bFunctionProtocol=0x20 (AF_VERSION_02_00)
  iFunction=0 (no string)

Interface Descriptor, IF 0: Audio Control (9 bytes)
  bLength=9, bDescriptorType=0x04 (INTERFACE)
  bInterfaceNumber=0
  bAlternateSetting=0
  bNumEndpoints=0              ← AC has no streaming endpoints
  bInterfaceClass=0x01 (AUDIO)
  bInterfaceSubClass=0x01 (AUDIO_CONTROL)
  bInterfaceProtocol=0x20 (AF_VERSION_02_00)
  iInterface=0 (no string)

Class-Specific AC Interface Header (9 bytes)
  bLength=9, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x01 (HEADER)
  bcdADC=0x0200 (Audio Device Class 2.0)
  bCategory=0x04 (DESKTOP_MICROPHONE)
  wTotalLength= (calculated)
  bmControls=0x00 (no latency control)

Clock Source Descriptor (8 bytes)
  bLength=8, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x0A (CLOCK_SOURCE)
  bClockID=1
  bmAttributes=0x01 (INTERNAL_FIXED_CLOCK)
  bmControls=0x00 (no frequency control)
  bAssocTerminal=0
  iClockSource=0

Input Terminal Descriptor — Microphone (17 bytes)
  bLength=17, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x02 (INPUT_TERMINAL)
  bTerminalID=2
  wTerminalType=0x0201 (MICROPHONE, GENERAL)
  bAssocTerminal=0
  bCSourceID=1 (Clock Source ID 1)
  bNrChannels=1 (Mono)
  bmChannelConfig=0x00000000 (MONO)
  iChannelNames=0
  bmControls=0x0000 (no gain/mute control on terminal)
  iTerminal=0

Output Terminal Descriptor — USB OUT (12 bytes)
  bLength=12, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x03 (OUTPUT_TERMINAL)
  bTerminalID=3
  wTerminalType=0x0101 (USB_STREAMING)
  bAssocTerminal=0
  bSourceID=2 (Input Terminal 2)
  bCSourceID=1 (Clock Source ID 1)
  bmControls=0x0000
  iTerminal=0

Status Endpoint (7 bytes) — Interrupt IN
  bLength=7, bDescriptorType=0x05 (ENDPOINT)
  bEndpointAddress=0x81 (IN, EP 1)
  bmAttributes=0x03 (INTERRUPT)
  wMaxPacketSize=8
  bInterval=2 (2ms polling)

Class-Specific EP Descriptor (8 bytes)
  bLength=8, bDescriptorType=0x25 (CS_ENDPOINT)
  bDescriptorSubtype=0x01 (GENERAL)
  bmControls=0x00
  bLockDelayUnits=0
  wLockDelay=0
```

## Interface 1: UAC2 Audio Streaming (Alternate Settings)

```text
--- Alternate Setting 0: No Streaming (Zero Bandwidth) ---
Interface Descriptor (9 bytes)
  bLength=9, bDescriptorType=0x04 (INTERFACE)
  bInterfaceNumber=1
  bAlternateSetting=0
  bNumEndpoints=0              ← NO endpoints (zero bandwidth)
  bInterfaceClass=0x01 (AUDIO)
  bInterfaceSubClass=0x02 (AUDIO_STREAMING)
  bInterfaceProtocol=0x20 (AF_VERSION_02_00)
  iInterface=0

--- Alternate Setting 1: Streaming Enabled ---
Interface Descriptor (9 bytes)
  bLength=9, bDescriptorType=0x04 (INTERFACE)
  bInterfaceNumber=1
  bAlternateSetting=1
  bNumEndpoints=1              ← ONE isochronous endpoint
  bInterfaceClass=0x01 (AUDIO)
  bInterfaceSubClass=0x02 (AUDIO_STREAMING)
  bInterfaceProtocol=0x20 (AF_VERSION_02_00)
  iInterface=0

Class-Specific AS Interface Descriptor (16 bytes)
  bLength=16, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x01 (GENERAL)
  bTerminalLink=3 (Output Terminal ID 3)
  bmControls=0x00 (no active alternate setting control)
  bFormatType=0x01 (FORMAT_TYPE_I — PCM)
  bmFormats=0x00000001 (PCM)
  bNrChannels=1 (Mono)
  bmChannelConfig=0x00000000 (MONO)
  iChannelNames=0

Isochronous Audio Data Endpoint (7 bytes) — Standard
  bLength=7, bDescriptorType=0x05 (ENDPOINT)
  bEndpointAddress=0x82 (IN, EP 2)
  bmAttributes=0x0D (ISOCHRONOUS, ADAPTIVE, DATA)
  wMaxPacketSize=32           ← 32 bytes/ms (16 samples × 2 bytes, mono 16-bit @ 16kHz)
  bInterval=1 (every microframe, 125μs)

Class-Specific AS Isochronous EP (8 bytes)
  bLength=8, bDescriptorType=0x25 (CS_ENDPOINT)
  bDescriptorSubtype=0x01 (GENERAL)
  bmAttributes=0x00 (no pitch control)
  bmControls=0x00
  bLockDelayUnits=0
  wLockDelay=0
```

## Interface 2: HID Keyboard

```text
Interface Descriptor (9 bytes)
  bLength=9, bDescriptorType=0x04 (INTERFACE)
  bInterfaceNumber=2
  bAlternateSetting=0
  bNumEndpoints=1
  bInterfaceClass=0x03 (HID)
  bInterfaceSubClass=0x01 (BOOT)
  bInterfaceProtocol=0x01 (KEYBOARD)
  iInterface=0

HID Descriptor (9 bytes)
  bLength=9, bDescriptorType=0x21 (HID)
  bcdHID=0x0111 (HID 1.11)
  bCountryCode=0x00 (Not localized)
  bNumDescriptors=1
  bDescriptorType=0x22 (REPORT)
  wDescriptorLength= (size of HID Report Descriptor)

Endpoint Descriptor (7 bytes) — Interrupt IN
  bLength=7, bDescriptorType=0x05 (ENDPOINT)
  bEndpointAddress=0x83 (IN, EP 3)
  bmAttributes=0x03 (INTERRUPT)
  wMaxPacketSize=8           ← 8-byte boot keyboard report
  bInterval=1 (1ms polling — 1000 Hz)
```

### HID Report Descriptor (Boot Keyboard)

```c
0x05, 0x01,        // Usage Page (Generic Desktop)
0x09, 0x06,        // Usage (Keyboard)
0xA1, 0x01,        // Collection (Application)
0x05, 0x07,        //   Usage Page (Keyboard/Keypad)
0x19, 0xE0,        //   Usage Minimum (Left Control)
0x29, 0xE7,        //   Usage Maximum (Right GUI)
0x15, 0x00,        //   Logical Minimum (0)
0x25, 0x01,        //   Logical Maximum (1)
0x75, 0x01,        //   Report Size (1)
0x95, 0x08,        //   Report Count (8)
0x81, 0x02,        //   Input (Data, Variable, Absolute) — Modifier byte
0x95, 0x01,        //   Report Count (1)
0x75, 0x08,        //   Report Size (8)
0x81, 0x01,        //   Input (Constant) — Reserved byte
0x95, 0x06,        //   Report Count (6)
0x75, 0x08,        //   Report Size (8)
0x15, 0x00,        //   Logical Minimum (0)
0x26, 0xFF, 0x00,  //   Logical Maximum (255)
0x05, 0x07,        //   Usage Page (Keyboard/Keypad)
0x19, 0x00,        //   Usage Minimum (Reserved)
0x29, 0xFF,        //   Usage Maximum (Reserved)
0x81, 0x00,        //   Input (Data, Array) — 6 key slots
0xC0               // End Collection
```

## Interface 3: CDC ACM (Virtual Serial Port)

```text
Interface Descriptor (9 bytes)
  bLength=9, bDescriptorType=0x04 (INTERFACE)
  bInterfaceNumber=3
  bAlternateSetting=0
  bNumEndpoints=1              ← notification endpoint only; data on IF 4
  bInterfaceClass=0x02 (CDC)
  bInterfaceSubClass=0x02 (ACM — Abstract Control Model)
  bInterfaceProtocol=0x01 (AT Commands: V.250)
  iInterface=0

CDC Header Functional Descriptor (5 bytes)
  bFunctionLength=5, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x00 (HEADER)
  bcdCDC=0x0110 (CDC 1.10)

CDC ACM Functional Descriptor (4 bytes)
  bFunctionLength=4, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x02 (ACM)
  bmCapabilities=0x02 (supports line coding and serial state)

CDC Union Functional Descriptor (5 bytes)
  bFunctionLength=5, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x06 (UNION)
  bControlInterface=3          ← IF 3 is the control interface
  bSubordinateInterface=4      ← IF 4 is the data interface

CDC Call Management Functional Descriptor (5 bytes)
  bFunctionLength=5, bDescriptorType=0x24 (CS_INTERFACE)
  bDescriptorSubtype=0x01 (CALL_MANAGEMENT)
  bmCapabilities=0x00 (no call management)
  bDataInterface=4

Endpoint Descriptor (7 bytes) — Interrupt IN (Notification)
  bLength=7, bDescriptorType=0x05 (ENDPOINT)
  bEndpointAddress=0x84 (IN, EP 4)
  bmAttributes=0x03 (INTERRUPT)
  wMaxPacketSize=8
  bInterval=16 (16ms — 64ms polling)

Interface Descriptor, IF 4: CDC Data (9 bytes)
  bLength=9, bDescriptorType=0x04 (INTERFACE)
  bInterfaceNumber=4
  bAlternateSetting=0
  bNumEndpoints=2
  bInterfaceClass=0x0A (CDC_DATA)
  bInterfaceSubClass=0x00
  bInterfaceProtocol=0x00
  iInterface=0

Endpoint Descriptor (7 bytes) — Bulk OUT (from host to device)
  bLength=7, bDescriptorType=0x05 (ENDPOINT)
  bEndpointAddress=0x02 (OUT, EP 2 OUT)
  bmAttributes=0x02 (BULK)
  wMaxPacketSize=64
  bInterval=0

Endpoint Descriptor (7 bytes) — Bulk IN (from device to host)
  bLength=7, bDescriptorType=0x05 (ENDPOINT)
  bEndpointAddress=0x85 (IN, EP 5)
  bmAttributes=0x02 (BULK)
  wMaxPacketSize=64
  bInterval=0
```

## String Descriptors

| Index | Language | Content |
|-------|----------|---------|
| 0 | 0x0409 (English-US) | Supported language list |
| 1 | 0x0409 | `"M5Stack"` |
| 2 | 0x0409 | `"Cardputer-Adv"` (configurable via NVS `device_name`) |
| 3 | 0x0409 | Unique serial (ESP32-S3 MAC-derived, e.g., `"CCB-3C6105"`) |

## macOS Enumeration Verification

After enumeration, macOS System Information (`system_profiler SPUSBDataType`) should show:

```text
Cardputer-Adv:
  Product ID: 0x4001
  Vendor ID: 0x303a
  Version: 1.00
  Serial Number: CCB-3C6105
  Speed: Up to 12 Mb/s

System Settings → Sound → Input should list:
  Cardputer-Adv (USB audio device)

System Settings → Keyboard → should see no changes
  (HID keyboard is transparent — works in any text field)

/dev/tty.usbmodem* should show:
  /dev/tty.usbmodemCCB-3C6105 (CDC serial port)
```

## macOS Enumeration Verification

Run `system_profiler SPUSBDataType` to verify the composite device enumerates correctly:

```bash
system_profiler SPUSBDataType | grep -A 10 "Cardputer-Adv"
```

Expected: Shows Vendor ID `0x303A`, Product ID `0x4001`, three interfaces listed.
