# Cartridge FRAM Memory Map (v1)

This document defines how FRAM I2C memory is used by `firmwareESP32S3.ino` to store cartridge metadata.

## Addressing model

- FRAM is byte-addressable.
- `framw<address>,<value>;` writes one byte (`0..255`) to one address.
- `framr<address>;` reads one byte from one address.
- Current firmware accepts addresses in `0..32767`.

## Reserved structure

| Address | Size | Name | Meaning |
|---|---:|---|---|
| 0 | 1 byte | `MAGIC0` | Fixed value `0x42` (`'B'`) |
| 1 | 1 byte | `MAGIC1` | Fixed value `0x50` (`'P'`) |
| 2 | 1 byte | `LAYOUT_VERSION` | Memory map version. Current value `0x01` |
| 3 | 1 byte | `SCRATCH` | Scratch byte used by `framchk;` write/read/restore test |
| 10 | 1 byte | `IDEAL_VOLT_INT` | Ideal detector voltage integer part (`40..50`) |
| 11 | 1 byte | `IDEAL_VOLT_DEC` | Ideal detector voltage decimal part (`0..99`) |
| 12..31 | 20 bytes | Reserved | Future cartridge metadata fields |

## Commands

- `framinit;`  
  Writes memory map header bytes at addresses `0,1,2`.

- `framchk;`  
  Verifies FRAM presence, checks header bytes, performs scratch write/read/restore at address `3`, and prints `FRAM_CHECK: PASS/FAIL`.

- `framw<address>,<value>;`  
  Writes one byte.

- `framr<address>;`  
  Reads one byte and prints `FRAM[address] = value`.

- `framvset<integer>,<decimal>;`  
  Stores ideal cartridge voltage split in two bytes at addresses `10` and `11`.

- `framv;`  
  Reads addresses `10` and `11` and prints `Ideal detector voltage: XX.YY V`.

## Manual voltage example

For ideal voltage `42.12 V`, you can either:

1) Use dedicated command:
- `framvset42,12;`

2) Or manually set with generic writer:
- `framw10,42;`
- `framw11,12;`

Then read back:
- `framv;`

## Future extension rule

When adding new fields:
1. Allocate new free addresses.
2. Update this document.
3. If layout is incompatible, increment `LAYOUT_VERSION` (address `2`).
