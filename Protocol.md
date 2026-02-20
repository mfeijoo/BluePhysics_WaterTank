# BluePhysics Serial Protocol (Binary-Only)

This protocol is **binary-only for device responses and data payloads**.

- Firmware commands are still sent as ASCII tokens terminated by `;` (example: `M10,25,-3;`).
- Firmware replies/data are binary packets only (`Serial.write(...)`), no human-readable `Serial.print` output.
- Output-mode commands `tb;` / `th;` are removed and must not be used.

---

## 1) Command format (Host -> Firmware)

ASCII command string terminated by semicolon:

- `z;`
- `P;`
- `p;`
- `b;`
- `i700;`
- `m2000;`
- `M10,25.5,-3;`
- `S10,25.5,-3;`
- `Q10,25.5,-3,2000;`
- `x200;`, `y-50;`, `z1000;`, `Y300;`

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

## 4) Move + measure packet (`Qx,y,z,N;`)

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

## 5) Coordinate compatibility packet (`b;`)

Legacy compact coordinate packet:

```text
AA 55 <int32 x><int32 y><int32 z>
```

- No `<type>` byte in this legacy variant.
- Prefer `P;` / `p;` with typed packet `AA 55 20 ...` for robust parsing.

---

## 6) Binary-only rules

1. Do not parse lines from firmware as text.
2. Do not send `tb;` or `th;`.
3. Treat all device responses/telemetry as binary packets.
4. Keep parser resynchronization logic based on packet headers (`AA55`, `ABCD`, `ADEF`).
