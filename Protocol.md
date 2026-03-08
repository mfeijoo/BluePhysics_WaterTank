# BluePhysics Serial Protocol (Binary + Human Debug)

This protocol is **binary-first** for device responses and data payloads, with a small set of human-readable debug commands.

- Firmware commands are still sent as ASCII tokens terminated by `;` (example: `M10,25,-3;`).
- Firmware replies/data are binary packets (`Serial.write(...)`) for production commands.
- Human-readable debug output is available on selected commands (for example `P;`, `start;`, and `stop;`).

---

## 1) Command format (Host -> Firmware)

ASCII command string terminated by semicolon:

- `z;`
- `p;`
- `P;`
- `L;`
- `l;`
- `b;`
- `i700;`
- `m2000;`
- `readbytes100;`
- `M10,25.5,-3;`
- `S10,25.5,-3;`
- `Q10,25.5,-3,2000;`
- `x200;`, `y-50;`, `z1000;`, `Z300;`
- `ux200;`, `uy-50;`, `uz1000;`, `uZ300;`

---

## 2) Common control packet framing (Firmware -> Host)

General control packets:

```text
AA 55 <type:1> <payload...>
```

### Type `0x10` ACK

```text
AA 55 10 <cmd_id:1>
```

- Total length: 4 bytes.
- `cmd_id` is the ASCII command byte (example: `'M'`, `'z'`, `'i'`).

### Type `0x11` ERROR

```text
AA 55 11 <cmd_id:1> <err_code:1>
```

- Total length: 5 bytes.
- `err_code` values used by current firmware:
  - `0x01`: malformed command payload.
  - `0x02`: argument out of range.
  - `0x03`: movement blocked by configured axis limit(s).

### Type `0x20` COORDS

```text
AA 55 20
<int32 x_cnt><int32 y_cnt><int32 z_cnt>
<float x_mm><float y_mm><float z_mm>
```

- Payload: 24 bytes.
- Total packet length: 27 bytes.
- All numeric fields are little-endian.

### Type `0x21` MOVE DONE

Same payload layout as `0x20` COORDS (end position).

### Type `0x22` ZERO DONE

Same payload layout as `0x20` COORDS (post-zero position).

### Type `0x23` PCNT32 LIMITS

```text
AA 55 23
<int32 x_min><int32 x_max>
<int32 y_min><int32 y_max>
<int32 z_min><int32 z_max>
```

- Payload: 24 bytes.
- Total packet length: 27 bytes.
- All numeric fields are little-endian.

---

## 3) Detector measurement packet (`m...`)

For `m;` / `mN;`, firmware emits one binary block:

```text
AB CD
<uint32 total_samples>
<uint32 integration_us>
N * [<uint32 dt_us><uint16 ch0><uint16 ch1>]
```

- Per-sample size: 8 bytes.
- Payload sample structure matches `struct Sample { uint32_t dt_us; uint16_t ch0; uint16_t ch1; }`.

---


## 4) Detector read-bytes packet (`readbytesN;`)

For `readbytesN;`, firmware first ACKs the command and then emits one binary block:

```text
AA 55 10 72
AA 55 31
<uint32 total_samples>
<uint32 integration_us>
N * [<uint32 idx><uint32 dt_us><uint16 ch0><uint16 ch1>]
```

- `72` is ASCII `'r'` in the ACK packet.
- Sample payload matches `struct Sample` in firmware (little-endian fields).

## 4.1) Detector byte-stream packets (`rs;` / `re;`)

`rs;` and `re;` use **binary packets** with the standard `AA 55 <type>` framing.

### Stream start (`rs;`)

Firmware sends:

```text
AA 55 10 73
AA 55 32
<uint32 integration_us>
```

- `73` is ASCII `'s'` in the ACK packet.

### Stream sample packets (while active)

Firmware emits one packet per integration period:

```text
AA 55 33
<uint32 idx>
<uint32 dt_us>
<uint16 ch0>
<uint16 ch1>
```

- Total packet size: 3 + 12 = 15 bytes.

### Stream stop (`re;`)

Firmware sends:

```text
AA 55 10 65
AA 55 34
<uint32 total_samples>
```

- `65` is ASCII `'e'` in the ACK packet.
- `total_samples` is the number of `0x33` sample packets sent in that streaming session.


- `start;` / `stop;` remain available for human-readable troubleshooting output over `Serial.print(...)`.

## 5) Move + measure packet (`Qx,y,z,N;`)

For `Q...`, firmware moves then emits:

```text
AD EF
<uint32 total_samples>
<uint32 integration_us>
<int32 x_end><int32 y_end><int32 z_end>
N * [<uint32 dt_us><uint16 ch0><uint16 ch1>]
```

- End coordinates are encoder counts (logical Z).
- Then follows the same sample payload format used by `AB CD` packets.

---

## 6) Coordinate compatibility packet (`b;`)

Legacy compact coordinate packet:

```text
AA 55 <int32 x><int32 y><int32 z>
```

- No `<type>` byte in this legacy variant.
- Prefer `p;` with typed packet `AA 55 20 ...` for robust parsing.

---

## 7) Human-readable debug commands (`P;`, `L;`)

`P;` prints raw 32-bit pulse counter values for all axes using `Serial.print(...)`:

```text
pcnt32 X: <int32>
pcnt32 Y: <int32>
pcnt32 Z: <int32>
```

- `P;` is intended for manual debugging in a serial monitor.
- It does **not** send a binary packet and does **not** emit ACK/ERR framing.


`L;` prints configured 32-bit pulse counter limits for all axes using `Serial.print(...)`:

```text
pcnt32 limits:
X min: <int32>, X max: <int32>
Y min: <int32>, Y max: <int32>
Z min: <int32>, Z max: <int32>
```

- `L;` is intended for manual debugging in a serial monitor.
- It does **not** send a binary packet and does **not** emit ACK/ERR framing.



## 7.1) Binary pcnt32 limits packet (`l;`)

For `l;`, firmware sends:

```text
AA 55 10 6C
AA 55 23
<int32 x_min><int32 x_max>
<int32 y_min><int32 y_max>
<int32 z_min><int32 z_max>
```

- `6C` is ASCII `'l'` in the ACK packet.
- `0x23` payload is little-endian and contains min/max bounds for each axis.

## 7.2) Set pcnt32 limits command (`lc...;`)

Set all axis limits in one command:

```text
lc<x_min>,<x_max>,<y_min>,<y_max>,<z_min>,<z_max>;
```

Example:

```text
lc-10000,10000,-9000,9000,-8000,8000;
```

Firmware response:

```text
AA 55 10 63
AA 55 23
<int32 x_min><int32 x_max>
<int32 y_min><int32 y_max>
<int32 z_min><int32 z_max>
```

Error responses:
- `AA 55 11 63 01` malformed command.
- `AA 55 11 63 02` invalid ranges (`min >= max` for any axis).

---


## 7.3) Unlimited direct step move command (`u<axis><steps>;`)

Move one axis (or coupled `Z`) by signed step count **without** limit checks:

```text
ux<steps>;
uy<steps>;
uz<steps>;
uZ<steps>;
```

Examples:

```text
ux200;
uy-50;
uz1000;
uZ300;
```

Firmware response:

```text
AA 55 10 75
AA 55 21
<int32 x_cnt><int32 y_cnt><int32 z_cnt>
```

- `75` is ASCII `'u'` in the ACK packet.
- `uZ...;` uses the same true coupled Y+Z step behavior as `Z...;` and applies the same Y logical-coordinate offset compensation used by limited coupled moves.
- Malformed `u` commands return `AA 55 11 75 01`.

## 8) Binary parser rules

1. For machine parsing, use binary-response commands (for coordinates use `p;`, for limits use `l;`, not `P;`/`L;`).
2. Limit-check failures for `x...;`, `y...;`, `z...;`, `Z...;`, and `M...;` are binary `0x11` error packets (no human-readable `Serial.print` diagnostics).
3. `u...;` bypasses axis-limit checks by design and still returns ACK + `0x21` move-done coordinates.
4. `lc...;` returns `ERR 0x01` on malformed syntax and `ERR 0x02` when any axis has `min >= max`.
5. Do not send `tb;` or `th;`.
6. Keep parser resynchronization logic based on packet headers (`AA55`, `ABCD`, `ADEF`).
7. Ignore human-readable text lines when using debug commands (`P;`, `start;`, `stop;`).
