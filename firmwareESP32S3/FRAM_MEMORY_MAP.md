# FRAM Memory Configuration (I2C 0x50)

This document defines how FRAM memory is currently used in `firmwareESP32S3`.

## Device and protocol

- **I2C address:** `0x50` (7-bit)
- **Memory addressing:** 16-bit memory address (`0x0000` to `0xFFFF`)
- **Access granularity:** 1 byte per read/write operation

Firmware command parser expects serial commands terminated with `;`.

## Current memory map

| FRAM address | Size | Name | Description |
|---|---:|---|---|
| `0x0000` | 1 byte | `optimal_voltage_integer` | Integer part of optimal operation voltage in volts. Example for 42.10 V: `42`. |
| `0x0001` | 1 byte | `optimal_voltage_decimal` | Two-digit decimal part of optimal operation voltage. Example for 42.10 V: `10`. |

## Encoding format

Optimal voltage is encoded as:

`voltage = integer_byte + (decimal_byte / 100.0)`

Example:
- `42.10 V` is stored as:
  - `0x0000 = 42`
  - `0x0001 = 10`

## Validation rules

- Integer byte range: `0..255`
- Decimal byte expected range: `0..99`
- `fcheck50;` reports data as **VALID** when decimal byte is in `0..99`.

## Related serial commands

- `ovset<voltage>;` → stores voltage into `0x0000` and `0x0001`
- `ovread;` → reads and prints decoded voltage
- `fcheck50;` → reads both bytes and reports whether stored format looks valid

## Reserved space (future use)

Addresses `0x0002` and above are currently free and reserved for future cartridge information.
