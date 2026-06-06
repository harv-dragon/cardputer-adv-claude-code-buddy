# HID Keyboard Report Format & Key Mapping

**Feature**: 001-deep-research-solutions
**Contract Type**: HID Report Descriptor & Key Mapping
**Version**: 1.0.0

## HID Report Format

The Cardputer-Adv presents as a standard USB HID Boot Keyboard. Reports follow the
8-byte boot keyboard format:

| Byte | Bits | Description |
|------|------|-------------|
| 0 | 0-7 | Modifier keys (bitmask) |
| 1 | 0-7 | Reserved (0x00) |
| 2 | 0-7 | Key slot 1 (HID usage code or 0x00) |
| 3 | 0-7 | Key slot 2 |
| 4 | 0-7 | Key slot 3 |
| 5 | 0-7 | Key slot 4 |
| 6 | 0-7 | Key slot 5 |
| 7 | 0-7 | Key slot 6 |

### Modifier Byte (Byte 0)

| Bit | Mask | Modifier |
|-----|------|----------|
| 0 | 0x01 | Left Control |
| 1 | 0x02 | Left Shift |
| 2 | 0x04 | Left Alt |
| 3 | 0x08 | Left GUI (Command on Mac) |
| 4 | 0x10 | Right Control |
| 5 | 0x20 | Right Shift |
| 6 | 0x40 | Right Alt |
| 7 | 0x80 | Right GUI (Command on Mac) |

## Cardputer-Adv Key → HID Usage Mapping (Default)

### Standard QWERTY Keys

The Cardputer-Adv has a 56-key (4 rows × 14 columns) QWERTY keyboard. Keys map to
standard USB HID keyboard usage codes per the USB HID Usage Tables specification.

| Cardputer Key | HID Usage ID | HID Usage Name | Notes |
|---------------|-------------|----------------|-------|
| `Q`-`P` (top row) | 0x14-0x19 | Keyboard q-p | Standard QWERTY |
| `A`-`;` (home row) | 0x04-0x0A, 0x33 | Keyboard a-; | Standard QWERTY |
| `Z`-`/` (bottom row) | 0x1D-0x24, 0x38 | Keyboard z-/ | Standard QWERTY |
| `1`-`0` (number row) | 0x1E-0x27 | Keyboard 1-0 | Standard number row |
| `` ` `` (backtick) | 0x35 | Keyboard ` and ~ | Char varies by Shift state |
| `-` | 0x2D | Keyboard - and _ | |
| `=` | 0x2E | Keyboard = and + | |
| `[` | 0x2F | Keyboard [ and { | |
| `]` | 0x30 | Keyboard ] and } | |
| `\` | 0x31 | Keyboard \ and \| | |
| `'` | 0x34 | Keyboard ' and " | |

### Modifier & Special Keys

| Cardputer Key | HID Usage ID | HID Usage Name | HID Modifier | Notes |
|---------------|-------------|----------------|--------------|-------|
| `Shift` (left) | — | — | 0x02 (Left Shift) | Modifier only, no usage code |
| `Shift` (right) | — | — | 0x20 (Right Shift) | Modifier only |
| `Ctrl` | — | — | 0x01 (Left Control) | Modifier only |
| `Alt` | — | — | 0x04 (Left Alt) | Modifier only |
| `Fn` | N/A | N/A | N/A | Internal modifier — changes keymap layer, NOT sent to host |
| `Space` | 0x2C | Keyboard Spacebar | — | Standard space |
| `Enter` | 0x28 | Keyboard Return | — | |
| `Backspace` | 0x2A | Keyboard Backspace | — | |
| `Tab` | 0x2B | Keyboard Tab | — | |
| `Esc` | 0x29 | Keyboard Escape | — | |
| `Up` | 0x52 | Keyboard Up Arrow | — | |
| `Down` | 0x51 | Keyboard Down Arrow | — | |
| `Left` | 0x50 | Keyboard Left Arrow | — | |
| `Right` | 0x4F | Keyboard Right Arrow | — | |
| `.` (period) | 0x37 | Keyboard . and > | — | |
| `,` (comma) | 0x36 | Keyboard , and < | — | |
| `'` (quote) | 0x34 | Keyboard ' and " | — | |

### Dictation Trigger Key (Special Mapping)

This is the critical key mapping for MacWhisper integration. The user presses and holds
a Cardputer key to trigger MacWhisper's "hold to dictate" feature.

**Default**: Hold `Space` → sends `Right GUI` (0x80 modifier + no usage code)

| Parameter | Default | Description |
|-----------|---------|-------------|
| Trigger key | `Space` (physical) | Which Cardputer key activates dictation |
| HID modifier | `0x80` (Right GUI) | HID modifier byte sent |
| HID usage | `0x00` (none) | HID usage code (0x00 = modifier-only) |
| Hold threshold | 200ms | How long the key must be held before HID report is sent |
| Release behavior | Release HID modifier | On physical key release, send report with modifier cleared |

**Configurable via NVS** (`dictation_key` and `dictation_modifier` fields):
- `Right Option` trigger: modifier = `0x40` (Right Alt)
- `Right Control` trigger: modifier = `0x10` (Right Control)
- `Function key` trigger: usage = `0x3A` (F1) through `0x45` (F12)

**MacWhisper Configuration**: User must configure MacWhisper to use the same trigger
key (Right Command or Right Option) as the Cardputer sends.

### Fn Layer Key Mappings

When `Fn` key is held, the keymap changes:

| Fn + Key | HID Usage ID | Function | Notes |
|----------|-------------|----------|-------|
| Fn + 1 | 0x3A | F1 | |
| Fn + 2 | 0x3B | F2 | |
| ... | ... | ... | |
| Fn + 0 | 0x43 | F10 | |
| Fn + - | 0x44 | F11 | |
| Fn + = | 0x45 | F12 | |
| Fn + Up | 0x4B | Volume Up | Media key |
| Fn + Down | 0x4A | Volume Down | Media key |
| Fn + Left | 0x70 | Previous Track | Media key |
| Fn + Right | 0x6F | Next Track | Media key |
| Fn + B | — | Brightness Up | Device-local (not sent to host) |
| Fn + N | — | Brightness Down | Device-local |

## HID Report Generation Rules

1. **Debounce**: 30ms debounce period. Key must be stable for 30ms before report is sent.
2. **6KRO**: Up to 6 simultaneous keys + modifiers (boot keyboard limit).
3. **Phantom key suppression**: If >6 non-modifier keys are pressed, report the first 6
   and suppress the rest (standard USB HID behavior).
4. **Key repeat**: After initial 500ms hold, repeat every 30ms.
5. **Empty report**: When all keys are released, send an all-zeros report immediately
   (not after debounce delay — release is always immediate).

## macOS Compatibility

- macOS recognizes boot keyboard HID reports natively.
- Right GUI (0x80) maps to Right Command on Mac.
- Right Alt (0x40) maps to Right Option on Mac.
- Ensure MacWhisper is configured to match the chosen trigger key.
