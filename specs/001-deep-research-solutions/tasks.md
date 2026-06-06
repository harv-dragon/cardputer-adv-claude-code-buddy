# Tasks: Solution Options Research — Cardputer-Adv Firmware

**Input**: Design documents from `specs/001-deep-research-solutions/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Not requested for this research-phase spec. Tasks focus on research execution, POC validation, and document finalization.

**Organization**: Tasks are grouped by user story from spec.md to enable independent research and validation of each technical dimension.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5 from spec.md)
- Include exact file paths in descriptions

## Path Conventions

- Research output: `specs/001-deep-research-solutions/` (documentation)
- POC code: `poc/` directory at repo root (throwaway validation code)
- Reference analysis: GitHub repos accessed via web, findings documented in research.md

---

## Phase 1: Setup & Environment (Shared Infrastructure)

**Purpose**: Prepare development environment and clone reference repositories for analysis

- [x] T001 Install PlatformIO and ESP32-S3 toolchain per quickstart.md prerequisites
- [x] T002 [P] Clone lshaf/unigeek to `poc/unigeek-base/` and verify it builds for Cardputer-Adv target
- [x] T003 [P] Clone atomic14/esp32-usb-uac-experiments to `poc/uac-reference/` and extract UAC2 descriptor files
- [x] T004 [P] Clone probadhabishayee/INMP441-with-ESP32-S3-USB-Microphone to `poc/i2s-mic-reference/` and extract I2S-to-UAC2 data flow pattern (repo not found — extracted patterns from atomic14 instead)
- [x] T005 [P] Clone anthropics/claude-desktop-buddy to `poc/buddy-reference/` and extract state machine + protocol schema
- [x] T006 Verify macOS environment: `system_profiler SPUSBDataType`, MacWhisper installed, Python 3.11+ with pyserial
- [x] T007 Install Python test dependencies: `pip install pyserial` and create `tools/test_sender.py` skeleton

---

## Phase 2: Foundational Research (Blocking Prerequisites)

**Purpose**: Complete baseline technical analysis that all POC validations depend on

**⚠️ CRITICAL**: No user story POC can begin until this phase is complete

- [x] T008 Analyze lshaf/unigeek codebase structure — document in `poc/unigeek-base/ANALYSIS.md`: module organization, build system, key APIs (M5Cardputer, TFT_eSPI), entry point, FreeRTOS usage, binary size per feature
- [x] T009 [P] Map Cardputer-Adv GPIO assignments from UniGeek pin definitions and cross-reference with M5Stack schematics — document in `poc/unigeek-base/PINMAP.md`
- [x] T010 [P] Extract USB HID implementation from UniGeek — identify where USB mode is configured, how HID reports are generated, and how to switch from Arduino USB stack to TinyUSB — document in `poc/unigeek-base/USB_ANALYSIS.md`
- [x] T011 [P] Extract ES8311 audio implementation from UniGeek — identify I2S config, codec init sequence, and determine if ADC/mic path exists or only speaker output — document in `poc/unigeek-base/AUDIO_ANALYSIS.md`
- [x] T012 [P] Download and review ES8311 datasheet — document ADC register map, clock configuration, mic bias, PGA gain range, and power-up sequence in `poc/es8311-registers.md`
- [x] T013 Identify TinyUSB configuration needed for UAC2 + HID + CDC composite on ESP32-S3 within Arduino framework — document `CFG_TUD_*` flags, endpoint budget, and descriptor layout in `poc/tinyusb-config.md`

**Checkpoint**: Foundation ready — all user story POCs can now proceed in parallel

---

## Phase 3: User Story 1 — Evaluate USB Composite Device Approaches (Priority: P1) 🎯 MVP

**Goal**: Prove that the Cardputer-Adv can enumerate as UAC2 microphone + HID keyboard composite device on macOS

**Independent Test**: Flash POC firmware → `system_profiler SPUSBDataType` shows both Audio and HID interfaces under a single device entry → System Settings → Sound → Input shows "Cardputer-Adv" microphone → keypresses appear in text editor

### Implementation for User Story 1

- [x] T014 [US1] Create `poc/usb-composite/` directory with minimal PlatformIO project that depends only on TinyUSB and ESP32-S3 board support (no M5Cardputer lib yet)
- [x] T015 [US1] Implement USB device descriptor (device, configuration, IAD) in `poc/usb-composite/src/usb_descriptors.c` per contracts/usb-descriptor.md — UAC2 Audio Control IF 0, Audio Streaming IF 1, HID Keyboard IF 2, CDC ACM IF 3
- [x] T016 [P] [US1] Implement UAC2 audio control + streaming descriptors (clock source, input terminal mic, output terminal USB, isochronous IN endpoint Alt 0/1) in `poc/usb-composite/src/usb_descriptors.c`
- [x] T017 [P] [US1] Implement HID keyboard descriptor and 8-byte boot keyboard report in `poc/usb-composite/src/hid_descriptors.c` per contracts/hid-reports.md
- [x] T018 [P] [US1] Implement CDC ACM descriptors (header, ACM, union, call management, notification EP, bulk IN/OUT) in `poc/usb-composite/src/usb_descriptors.c` per contracts/usb-descriptor.md
- [x] T019 [US1] Implement TinyUSB device task and main loop in `poc/usb-composite/src/main.cpp` — initialize TinyUSB, handle UAC2 callbacks (stub with silence), HID report loop (send test key every 5s), CDC serial echo
- [x] T020 [US1] Configure PlatformIO build flags in `poc/usb-composite/platformio.ini` for TinyUSB with CFG_TUD_AUDIO=1, CFG_TUD_HID=1, CFG_TUD_CDC=1 on ESP32-S3
- [ ] T021 [US1] Build, flash to Cardputer-Adv, and verify macOS enumeration: `system_profiler SPUSBDataType` shows composite device with Audio + HID + CDC interfaces
- [ ] T022 [US1] Verify HID keyboard: press Cardputer keys → characters appear in macOS text editor
- [ ] T023 [US1] Verify CDC serial: `screen /dev/tty.usbmodem* 115200` → send test message → receive echo
- [ ] T024 [US1] Document USB composite enumeration results, any descriptor issues discovered, and macOS quirks in `poc/usb-composite/RESULTS.md`

**Checkpoint**: USB composite device (UAC2 + HID + CDC) proven viable on Cardputer-Adv

---

## Phase 4: User Story 2 — Select Audio Pipeline Architecture (Priority: P1)

**Goal**: Prove ES8311 MEMS microphone capture works on Cardputer-Adv and streams to macOS via UAC2 with acceptable latency and quality

**Independent Test**: Flash POC firmware → speak into Cardputer → macOS receives clean 16kHz mono audio → record in QuickTime → playback confirms voice quality → measure latency <30ms

### Implementation for User Story 2

- [x] T025 [US2] Create `poc/es8311-capture/` directory extending the USB composite POC with ES8311 + I2S capture support
- [x] T026 [US2] Configure I2C bus (GPIO8 SDA, GPIO9 SCL) and verify ES8311 responds at address 0x18 — read CHIP_ID register (0x2E) in `poc/es8311-capture/src/es8311_init.cpp`
- [x] T027 [US2] Implement ES8311 ADC initialization: clock config for 16kHz, power-up ADC, set I2S format (Philips 16-bit), configure PGA gain +30dB, enable mic bias, unmute ADC — in `poc/es8311-capture/src/es8311_init.cpp`
- [x] T028 [P] [US2] Configure ESP32-S3 I2S in RX master mode (BCLK=GPIO41, WS=GPIO43, DIN=GPIO46) for 16-bit 16kHz mono capture with 4 DMA descriptors × 256 samples in `poc/es8311-capture/src/i2s_capture.cpp`
- [x] T029 [US2] Implement PCM ring buffer (1024 samples, lock-free atomic read/write pointers) in `poc/es8311-capture/src/ring_buffer.h`
- [x] T030 [US2] Connect I2S RX DMA callback → ring buffer write in `poc/es8311-capture/src/i2s_capture.cpp`
- [x] T031 [US2] Implement UAC2 TX callback: read from ring buffer → `tud_audio_n_write()` → 16 samples per 1ms frame in `poc/es8311-capture/src/uac2_mic.cpp`
- [x] T032 [US2] Implement USB audio alternate setting handling: Alt 0 = stop I2S + stop streaming, Alt 1 = start I2S + start streaming in `poc/es8311-capture/src/uac2_mic.cpp`
- [ ] T033 [US2] Build, flash, and verify: macOS System Settings → Sound → Input shows Cardputer-Adv with active level meter when speaking
- [ ] T034 [US2] Measure audio pipeline latency: record tap-test (tap mic → observe waveform in Audacity) — document in `poc/es8311-capture/LATENCY.md`
- [ ] T035 [US2] Measure audio quality: record 10s of test speech, compare SNR to MacBook built-in mic — document in `poc/es8311-capture/QUALITY.md`
- [ ] T036 [US2] Stress test: continuous audio streaming for 10 minutes — verify zero dropped samples, no buffer overruns/underruns — document in `poc/es8311-capture/STRESS_TEST.md`

**Checkpoint**: ES8311 microphone capture + UAC2 streaming proven with latency <30ms

---

## Phase 5: User Story 3 — Choose Display/UI Framework (Priority: P2)

**Goal**: Prove TFT_eSPI can render all 3 display modes (Agent Status, Audio VU, Idle) and 4 agent states on the ST7789V2 240×135 screen within 64KB heap budget

**Independent Test**: Flash POC firmware → screen renders mock agent status at ≥15 FPS → free heap >64KB → mode transitions are flicker-free → text readable at arm's length

### Implementation for User Story 3

- [x] T037 [US3] Create `poc/display-ui/` directory extending the USB composite POC with TFT_eSPI display support
- [x] T038 [US3] Configure TFT_eSPI for Cardputer-Adv ST7789V2 (CS=37, DC=34, MOSI=35, SCLK=36, BL=38, RST=33, 240×135, 40MHz SPI) in `poc/display-ui/src/display_config.h`
- [x] T039 [US3] Implement Idle Mode screen: connection status icon, battery percentage bar, clock (HH:MM), device name — in `poc/display-ui/src/ui_idle.cpp`
- [x] T040 [US3] Implement Agent Status Mode screen: agent name, state badge (colored), runtime counter, token count, last 3 output lines with scrolling — in `poc/display-ui/src/ui_agent_status.cpp`
- [x] T041 [P] [US3] Implement Audio VU Mode screen: recording indicator, VU meter bar (animated), dBFS level text — in `poc/display-ui/src/ui_audio_vu.cpp`
- [x] T042 [P] [US3] Implement Permission Overlay: full-screen red pulsing border, permission hint text, "[SPACE] Approve [ESC] Deny" prompt — in `poc/display-ui/src/ui_permission.cpp`
- [x] T043 [US3] Implement display mode switcher with priority: waiting_permission > error > running > audio_input > idle — in `poc/display-ui/src/ui_mode_manager.cpp`
- [x] T044 [US3] Implement dirty rectangle tracking for partial screen updates (only redraw changed text/regions) in `poc/display-ui/src/ui_mode_manager.cpp`
- [ ] T045 [US3] Integrate with mock status data: cycle through all 4 states with 5-second intervals — measure FPS via frame counter and free heap via `esp_get_free_heap_size()` in `poc/display-ui/src/main.cpp`
- [ ] T046 [US3] Verify: all 3 modes render correctly, FPS ≥15, heap >64KB, text readable at arm's length, transitions are flicker-free — document in `poc/display-ui/RESULTS.md`

**Checkpoint**: Display UI proven with TFT_eSPI meeting all performance and memory targets

---

## Phase 6: User Story 4 — Define Host Communication Protocol (Priority: P2)

**Goal**: Prove the USB CDC serial JSON protocol works end-to-end: Mac Python script → CDC serial → device JSON parser → display update within 200ms

**Independent Test**: Run test_sender.py → Cardputer screen updates agent status in <200ms → send 1000 rapid messages → verify zero dropped (sequence check) → disconnect/reconnect cable → verify auto-recovery

### Implementation for User Story 4

- [x] T047 [US4] Extend POC with CDC serial JSON protocol support in `poc/host-comm/` (copy working USB composite POC)
- [x] T048 [US4] Implement newline-delimited JSON frame reader on CDC serial RX: buffer bytes until `\n`, parse JSON, validate `seq` field — in `poc/host-comm/src/protocol_parser.cpp`
- [x] T049 [P] [US4] Implement JSON→AgentStatus struct parser for all 4 message types (status, permission, log, config) using ArduinoJson v7 with schema validation — in `poc/host-comm/src/protocol_parser.cpp`
- [x] T050 [P] [US4] Implement dropped frame detection: track `seq` monotonic counter, log gaps, trigger full display refresh when state changes across dropped frames — in `poc/host-comm/src/protocol_parser.cpp`
- [x] T051 [P] [US4] Implement host disconnect detection: 5-second data timeout → set state to error with "Host disconnected" message — in `poc/host-comm/src/host_monitor.cpp`
- [x] T052 [US4] Connect protocol parser output → display mode manager to update UI on each valid status message in `poc/host-comm/src/main.cpp`
- [x] T053 [US4] Create `tools/test_sender.py`: Python script that connects to CDC serial port and sends mock AgentStatus JSON frames (cycle through all 4 states, increment seq) at configurable rate
- [ ] T054 [US4] End-to-end latency test: test_sender.py sends message with timestamp → device receives and renders → measure delta — document in `poc/host-comm/LATENCY.md` (target <200ms)
- [ ] T055 [US4] Reliability test: test_sender.py sends 1000 messages at 10ms intervals → verify device receives all with correct seq order → document in `poc/host-comm/RELIABILITY.md`
- [ ] T056 [US4] Disconnect/reconnect test: unplug USB → verify device shows "Disconnected" → replug → verify status resumes without reset — document in `poc/host-comm/RECOVERY.md`

**Checkpoint**: Host-to-device protocol proven reliable with <200ms latency and auto-recovery

---

## Phase 7: User Story 5 — Compare Firmware Frameworks (Priority: P3)

**Goal**: Execute UniGeek strip-down, add UAC2+I2S capture modules, measure binary size and heap, and validate the Arduino-as-Component hybrid approach

**Independent Test**: Build stripped UniGeek → binary <700KB → add UAC2+I2S+CDC+UI modules → rebuild → binary <1MB → flash → all retained features work → free heap >64KB

### Implementation for User Story 5

- [ ] T057 [US5] Fork lshaf/unigeek to `firmware/` directory and create `cardputer-adv-ccb` branch
- [ ] T058 [US5] Remove unneeded features from UniGeek fork per plan.md Section 4: BadUSB, Wi-Fi tools, WebAuthn, IR apps, password manager, BLE HID, non-Cardputer-Adv board targets, utility apps — verify each removal compiles
- [ ] T059 [US5] Measure binary size after strip-down: build and record .bin size — verify <700KB target — document in `firmware/SIZE_REPORT.md`
- [ ] T060 [P] [US5] Switch UniGeek USB stack from Arduino USB to TinyUSB: update platformio.ini with CFG_TUD flags, migrate HID keyboard to TinyUSB HID API in `firmware/src/usb_stack/hid_kbd.cpp`
- [ ] T061 [P] [US5] Add UAC2 microphone module to firmware: integrate TinyUSB UAC2 descriptors from POC T015-T018, I2S capture from POC T026-T030, UAC2 callbacks from POC T031-T032 into `firmware/src/usb_stack/` and `firmware/src/audio_pipeline/`
- [ ] T062 [P] [US5] Add CDC serial protocol module to firmware: integrate JSON parser from POC T048-T051 into `firmware/src/host_comm/`
- [ ] T063 [P] [US5] Add display UI module to firmware: integrate UI rendering from POC T039-T044 into `firmware/src/display_ui/`
- [ ] T064 [US5] Measure final binary size and free heap: build complete firmware → record .bin size → flash → read `esp_get_free_heap_size()` → verify <1MB and >64KB — document in `firmware/SIZE_REPORT.md`
- [ ] T065 [US5] Run full feature regression: USB HID keyboard → works, ES8311 speaker (if any) → works, ST7789 display → works, battery ADC → works, SD card → works — document in `firmware/REGRESSION.md`
- [ ] T066 [US5] Document framework evaluation: compare Arduino (UniGeek base) vs ESP-IDF (pure) vs Hybrid (Arduino-as-Component) with scored criteria per spec.md Section 5 — final recommendation in `firmware/FRAMEWORK_DECISION.md`

**Checkpoint**: UniGeek-based firmware proven viable with all modules integrated

---

## Phase 8: PRD & Execution Plan Finalization

**Purpose**: Synthesize all research findings, POC results, and design artifacts into a comprehensive Product Requirements Document and final Execution Plan

- [ ] T067 [P] Write PRD (Product Requirements Document) synthesizing all research: problem statement, user personas, product overview, functional requirements, non-functional requirements, technical architecture, and success metrics — save to `specs/001-deep-research-solutions/PRD.md`
- [ ] T068 [P] Finalize execution plan with POC-validated estimates: update plan.md Phase 1-3 timelines with actual POC results, revise risk register based on POC findings, add go/no-go decision criteria for each phase
- [ ] T069 [P] Generate bill of materials and dependencies: list all libraries with versions validated during POCs, all tools required, all reference repos with commit hashes — save to `specs/001-deep-research-solutions/BOM.md`
- [ ] T070 Create architecture decision records (ADR) for the 10 key decisions from research.md: decision title, status, context, decision, consequences — save to `specs/001-deep-research-solutions/decisions/` (one file per decision)
- [ ] T071 Update quickstart.md with lessons learned from POC execution: any platform-specific gotchas, troubleshooting additions, verified command sequences
- [ ] T072 [P] Generate final research summary: one-page executive summary of all findings, recommended architecture stack, confidence level for each decision (High/Medium/Low based on POC validation) — save to `specs/001-deep-research-solutions/SUMMARY.md`
- [ ] T073 Validate all generated documents pass spec quality checklist (specs/001-deep-research-solutions/checklists/requirements.md) — fix any regressions
- [ ] T074 Create handoff document for firmware implementation phase: what's decided, what's POC-validated, what still needs validation, reference code pointers, known issues — save to `specs/001-deep-research-solutions/HANDOFF.md`

**Checkpoint**: All research deliverables complete — comprehensive solution, PRD, and execution plan ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (reference repos cloned) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (USB analysis complete) — USB composite is the core enabler
- **User Story 2 (Phase 4)**: Depends on Phase 2 (audio analysis complete) + US1 (USB composite working) — audio streams over USB
- **User Story 3 (Phase 5)**: Depends on Phase 2 (display analysis) + US1 (USB working for CDC) — can start in parallel with US2
- **User Story 4 (Phase 6)**: Depends on Phase 2 + US1 (CDC serial working) — can start in parallel with US2 and US3
- **User Story 5 (Phase 7)**: Depends on US1, US2, US3, US4 (integrates all POC modules into UniGeek base)
- **PRD & Finalization (Phase 8)**: Depends on US1-US5 (synthesizes all POC results)

### User Story Dependencies

```
Phase 1 (Setup)
    │
Phase 2 (Foundational)
    │
    ├── Phase 3: US1 (USB Composite) ── BLOCKS US2, US4 ──┐
    │                                                       │
    ├── Phase 5: US3 (Display UI) ─────────────────────────┤
    │    (can start after Phase 2)                           │
    │                                                       │
    └── Phase 7: US5 (Firmware Framework) ←─────────────────┘
              (requires US1, US2, US3, US4 complete)
              │
              └── Phase 8 (PRD & Finalization)
                    
    US2 (Audio Pipeline) ── starts after US1 USB working
    US4 (Host Protocol)  ── starts after US1 CDC serial working
    US3 (Display UI)     ── starts after Phase 2 (independent of US1)
```

### Within Each User Story

1. Create directory and project structure
2. Implement infrastructure (descriptors, drivers, configs) — [P] tasks in parallel
3. Wire up pipeline (audio: I2S → ring buffer → UAC2; protocol: CDC → JSON → display)
4. Integration test and measure
5. Document results

---

## Parallel Opportunities

### Phase 1 (Setup)
```bash
# All clone tasks can run in parallel:
T002: Clone lshaf/unigeek
T003: Clone atomic14/esp32-usb-uac-experiments
T004: Clone probadhabishayee/INMP441-ESP32-S3-USB-Mic
T005: Clone anthropics/claude-desktop-buddy
```

### Phase 2 (Foundational)
```bash
# All analysis tasks can run in parallel:
T009: Map GPIO assignments
T010: Extract USB HID implementation
T011: Extract ES8311 audio implementation
T012: Review ES8311 datasheet
```

### Phase 3-6 (User Stories)
```bash
# US2 and US3 and US4 can run in parallel after US1 completes:
US2: Audio pipeline POC (T025-T036)
US3: Display UI POC (T037-T046)
US4: Host protocol POC (T047-T056)
```

### Phase 8 (PRD & Finalization)
```bash
# All documentation tasks can run in parallel:
T067: Write PRD
T068: Finalize execution plan
T069: Generate BOM
T072: Write executive summary
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T013)
3. Complete Phase 3: US1 USB Composite (T014-T024)
4. **STOP and VALIDATE**: Verify macOS enumerates composite device with all 3 interfaces
5. Decision gate: If USB enumeration fails, pivot to pure ESP-IDF approach before investing in US2-US5

### Incremental Delivery

1. Phase 1-2: Environment + analysis → Foundation ready
2. US1: USB composite → **Gate check**: proven or pivot
3. US2 + US3 + US4: Audio + Display + Protocol (parallel) → Core validated
4. US5: Full integration into UniGeek → Architecture proven
5. Phase 8: All documents finalized → Handoff ready

### Decision Gates

| Gate | After Phase | Go Criteria | No-Go Action |
|------|------------|-------------|--------------|
| USB Enumeration | Phase 3 (US1) | macOS shows Audio + HID + CDC composite | Pivot to pure ESP-IDF; re-evaluate timeline |
| Audio Pipeline | Phase 4 (US2) | Latency <30ms, zero dropped samples | Try esp_codec_dev; adjust sample rate to 8kHz |
| Full Integration | Phase 7 (US5) | Binary <1MB, heap >64KB, all features work | Strip more UniGeek features; optimize memory |

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story from spec.md
- Each user story produces a standalone POC that can be validated independently
- POC code in `poc/` is throwaway — patterns are captured in `firmware/` during US5
- Commit after each checkpoint (end of each Phase)
- All POC results feed into Phase 8 documentation
- Reference repos MUST be pinned to specific commit hashes in BOM.md (T069)
- Estimated total effort: ~15 working days (3 weeks) for all 74 tasks
