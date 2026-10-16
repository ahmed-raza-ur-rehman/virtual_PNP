# Interface Control Document (ICD)

**Document:** VP-ICD-001 · **Version:** 2.1
All numeric formats here are normative: firmware, RTL and host tools must agree
with this document, and any change to it is a breaking change.

---

## 1. Coordinate system and datums

* Origin: the **machine datum**, the left-front corner of the gantry envelope.
* X: right, Y: back (into the machine), Z: **up** (positive Z lifts the nozzle).
* Units: millimetres for the HMI and job files; **Q12.4 micrometres** (1 LSB =
  1/16 µm = 62.5 nm) on the wire.
* Rotation: degrees, counter-clockwise seen from above; **Q8.8** on the wire
  (1 LSB = 1/256°).
* Board fiducials: at least three, numbered F1…Fn, placed in the job file in
  board coordinates; the homography maps board → machine coordinates.

## 2. Register map (CSR bank)

Addresses are byte offsets; the host writes with byte enables, so a 32-bit
register may be updated byte by byte without a read-modify-write race.

| Offset | Name | Access | Description |
| --- | --- | --- | --- |
| 0x00 | CTRL | RW | bit0 enable, bit1 start, bit2 stop, bit3 clear faults |
| 0x04 | STATUS | RO | bit0 busy, bit1 at target, bit2 fault, bit3 link ok |
| 0x08 | AXIS_TGT | RW | target position, Q12.4 µm |
| 0x0C | AXIS_POS | RO | measured position, Q12.4 µm |
| 0x10 | V_MAX | RW | Q12.4 µm/s |
| 0x14 | A_MAX | RW | Q12.4 µm/s² |
| 0x18 | J_MAX | RW | Q12.4 µm/s³ |
| 0x1C | PID_KP | RW | Q4.12 |
| 0x20 | PID_KI | RW | Q4.12 |
| 0x24 | PID_KD | RW | Q4.12 |
| 0x28 | WD_KICK | WO | any write feeds the window watchdog |
| 0x2C | ERR_STAT | RW1C | sticky faults; write 1 to clear a bit |
| 0x30 | VERSION | RO | {major, minor, patch, build} |

## 3. Host protocol (SPI mode 0 or UART 8N1)

```
| 0xAA | 0x55 | CMD | LEN(1..8) | PAYLOAD[LEN] | CRC16-hi | CRC16-lo |
```

* CRC-16/CCITT-FALSE: polynomial 0x1021, init 0xFFFF, no reflection,
  **covering CMD, LEN and PAYLOAD only** (not the sync bytes, not the CRC).
* LEN = 0 or > 8 is a length error.  A frame that stops mid-way for more than
  `TIMEOUT` clocks is a timeout error; both increment the error counter.
* A frame is forwarded to the register file only after the CRC has been
  verified.

Commands:

| CMD | Name | Payload | Effect |
| --- | --- | --- | --- |
| 0x01 | WRITE | addr, data[4] | register write with byte enables |
| 0x02 | READ | addr | register read, answered in the telemetry stream |
| 0x03 | START | – | start the loaded move |
| 0x04 | KICK | – | feed the watchdog |
| 0x05 | CLEAR | – | clear the latched faults |

Telemetry frame (host ← machine, every `TELEM_DIV` clocks):

```
| 0xAA | 0x55 | 0x30 | flags | pos[15:8] | pos[7:0] | frames_ok | frames_err |
```

## 4. Encoder and drive interface

| Signal | Direction | Levels | Notes |
| --- | --- | --- | --- |
| ENC_A/B | in | TTL, quadrature | 4× decoding, debounced (4 samples) |
| ENC_IDX | in | TTL | latches `index_pos` for electrical homing |
| STEP | out | 3.3 V, 1 µs min pulse | DDA output, one pulse per count |
| DIR | out | 3.3 V | 1 = increasing position |
| LIMIT_x | in | active low | debounced 8 samples, latching |
| ESTOP_N | in | active low | same path as the limits |

## 5. Software interfaces

| Interface | Producer | Consumer | Contract |
| --- | --- | --- | --- |
| `pnp.optimization.optimize_placement` | planner | simulator, CLI, API | returns the same targets, reordered; never loses a target |
| `pnp.planning.s_curve_1d` | planner | motion, RTL reference | monotone, ends exactly on the target |
| `tools/rtlsim` | RTL | verification | consumes the yosys JSON netlist; unsupported cells are an error |
| `asic.miniflow` | RTL netlist | layout | consumes the same JSON; unknown gates are an error, never dropped |

## 6. Error model

| Fault | Where raised | Latch | Cleared by |
| --- | --- | --- | --- |
| CRC mismatch | `packet_if` | sticky flag + counter | CTRL.clear (bit 3) |
| Length out of range | `packet_if` | sticky flag + counter | CTRL.clear |
| Link timeout | `packet_if` | sticky flag + counter | CTRL.clear |
| Watchdog early kick | `watchdog_wwdg` | `early_kick` | CTRL.clear |
| Watchdog late kick | `watchdog_wwdg` | `reset_req`, `late_kick` | CTRL.clear while safe |
| Limit / e-stop asserted | `limit_monitor` | `latched`, `fault` | CTRL.clear **while all channels read safe** |
| Unknown command | `pnp_core` decoder | `cmd_decode_err` | CTRL.clear |

## 7. Timing

| Parameter | Value | Notes |
| --- | --- | --- |
| Logic clock | 100 MHz target, 10 ns period | synthesis report per block |
| SPI clock | ≤ 10 MHz | byte-per-8-clock transfer |
| UART | 921 600 8N1 default | 115 200 for the test benches |
| Watchdog window | 64 … 200 000 clocks | parameters `WIN_LOW`, `WIN_HIGH` |
| Control sample | 1 kHz (÷10 of a 10 kHz tick) | `sample_en` in `pnp_core` |
