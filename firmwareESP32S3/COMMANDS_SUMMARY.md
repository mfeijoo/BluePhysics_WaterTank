# firmwareESP32S3 Command Summary

All firmware commands are received over serial and must be terminated with a semicolon (`;`).

## General / Status

| Command | What it does |
|---|---|
| `t;` | Reads the MCP9808 temperature sensor and prints temperature in °C. |
| `fram;` | Checks FRAM presence on `0x50` and `0x51`. If library init succeeds, prints selected address + manufacturer/product IDs; if only ACK is seen, it still reports FRAM detected (presence confirmed) and notes IDs are unavailable. |
| `fram50;` | Simple presence check for the fixed FRAM device at `0x50`. |
| `fcheck50;` | Reads FRAM `0x50` addresses `0x0000` and `0x0001` (optimal voltage integer + decimal bytes) and reports whether stored format looks valid (`decimal <= 99`). |
| `ovset<voltage>;` | Stores optimal operation voltage in FRAM `0x50` using two bytes: integer part at `0x0000` and 2-digit decimal part at `0x0001`. Example: `ovset42.10;`. |
| `ovread;` | Reads and prints optimal operation voltage from FRAM `0x50` addresses `0x0000` and `0x0001`. |
| `fw50<mem_addr>,<value>;` | Simple byte write on fixed FRAM `0x50` (`mem_addr` 16-bit, `value` 8-bit). Examples: `fw500,123;`, `fw50256,171;` (hex also accepted, e.g. `fw500x0100,0xAB;`). |
| `fr50<mem_addr>;` | Simple byte read on fixed FRAM `0x50`. Examples: `fr500;`, `fr50256;` (hex also accepted, e.g. `fr500x0100;`). |
| `i2cscan;` | Temporary diagnostic scan of the I2C bus (SDA=8, SCL=9, 100 kHz); prints every detected 7-bit address (useful to verify FRAM at `0x50`). |
| `fwrite<dev_addr>,<mem_addr>,<value>;` | Raw byte write to I2C memory-style FRAM/EEPROM (`dev_addr` 7-bit, `mem_addr` 16-bit, `value` 8-bit). Examples: `fwrite0x50,0,123;`, `fwrite0x51,0x0100,0xAB;`. |
| `fread<dev_addr>,<mem_addr>;` | Raw byte read from I2C memory-style FRAM/EEPROM. Examples: `fread0x50,0;`, `fread0x51,0x0100;`. |
| `info;` | Prints device model and firmware version. |
| `eh0;` | Sets error reporting to binary packet mode. |
| `eh1;` | Sets error reporting to human-readable serial text mode. |

## Coordinates / Motion State

| Command | What it does |
|---|---|
| `z;` | Zeroes X/Y/Z encoder counters and clears the Y logical offset; then sends updated coordinates. |
| `p;` | Sends current coordinates as a binary packet. |
| `P;` | Prints raw 32-bit PCNT values for X, Y, Z in human-readable text. |
| `ps0;` | Reads and prints current PS0 voltage. |

## Limits and Step Timing

| Command | What it does |
|---|---|
| `L;` | Prints current X/Y/Z PCNT software limits in human-readable text. |
| `l;` | Sends current X/Y/Z PCNT software limits as a binary packet. |
| `lc<xmin>,<xmax>,<ymin>,<ymax>,<zmin>,<zmax>;` | Updates software travel limits for all three axes and returns updated limits packet. |
| `D;` | Prints current step pulse and gap times in microseconds. |
| `d;` | Sends current step pulse and gap times as a binary packet. |
| `stepdelays<pulse_us>,<gap_us>;` | Sets STEP high-time (`pulse_us`) and low-time (`gap_us`) in microseconds. |

## Detector / Integration

| Command | What it does |
|---|---|
| `i<us>;` | Sets detector integration time in microseconds (clamped internally to 50..50000 µs). |
| `it;` | Sends current detector integration time as a binary packet (`0x25`) with a `uint32` payload in microseconds. |
| `itime;` | Prints current detector integration time in microseconds in human-readable text. |
| `cint;` | Selects internal capacitor (`CAP_SEL_0` LOW) and prints capacitor state. |
| `cext;` | Selects external capacitor (`CAP_SEL_0` HIGH) and prints capacitor state. |
| `cstate;` | Prints current capacitor selection state. |
| `avgdet<0|1>[,<N>];` | Measures detector channel `0` or `1` repeatedly and prints the average in **volts** (and counts). Defaults to `N=100` when omitted. Example: `avgdet1,250;`. |
| `read<N>;` | Performs `N` detector reads and prints human-readable results. |
| `readbytes<N>;` | Performs `N` detector reads and sends them in binary format. |
| `start;` | Starts continuous human-readable detector stream (`idx, dt_us, ch0, ch1`). |
| `stop;` | Stops continuous human-readable detector stream. |
| `rs;` | Starts continuous binary detector stream. |
| `re;` | Stops continuous binary detector stream. |
| `pin21H;` | Forces GPIO21 (`SERIAL_TIMING_PIN`) to HIGH for debug/oscilloscope checks. |
| `pin21L;` | Forces GPIO21 (`SERIAL_TIMING_PIN`) to LOW for debug/oscilloscope checks. |
| `rsp[<threshold>[,<ACR>,<CF>]];` | Starts pulse-count mode on CH0 with optional threshold in volts and optional dose factors (`ACR`, `CF`). Defaults: `threshold=-9.0`, `ACR=1.0`, `CF=1.0`. During `rsp`, detector samples are streamed in the **same binary packet format as `rs;`**. Examples: `rsp;`, `rsp-9.2;`, `rsp-9.2,1.0,1.0;`, `rsp,1.0,1.0;`. |
| `re;` | Stops continuous binary detector stream, or if `rsp...;` is active, stops pulse-count mode with the same binary stop packet format as `rs;` and then prints totals (pulses, coincide pulses, accumulated dose) in human-readable text. |
| `rts;` | Starts continuous binary detector stream with temperature (detector + MCP9808 raw temp bytes). |
| `rte;` | Stops continuous binary detector+temperature stream. |

## Dark Current DAC (AD5675)

| Command | What it does |
|---|---|
| `dc<0|1>,<0-65535>;` | Sets AD5675 dark-current compensation DAC code for channel 0 or 1. Examples: `dc0,3000;`, `dc1,65535;`. |
| `sdc[1-100];` | Runs automatic dark-current setup for both channels: starts each channel at DAC code `0`, measures with 100 samples, increments DAC code by the selected step (`1..100`) while average voltage is above `0 V`, and stops when average is `<= 0 V` (or max DAC code is reached). `sdc;` defaults to step `10`, while `sdc20;` uses step `20`. During the loop, firmware prints status lines with current code, active channel voltage, and both channel volt/count averages. Sequence runs for ch0 first, then ch1. |
| `sdcv[<target_v>][,<step>];` | Runs automatic dark-current setup with configurable target voltage (float) and optional code step. Valid target range is `-10.5 .. 0.0 V` and valid `step` is integer `1..100`. Defaults: target `-10.0 V`, step `10` (`sdcv;`). Examples: `sdcv-10.2;`, `sdcv-10.2,25;`, `sdcv,25;`. Runs ch0 then ch1. Detector voltage is computed from counts using project formula `V = -((counts * 24.0) / 65535.0) + 12.0`. |
| `sdcstop;` | Requests cancellation of an in-progress `sdc...;` or `sdcv...;` routine. If no dark-current routine is active, firmware prints a no-op status message. |

## Power Supply / Potentiometer

| Command | What it does |
|---|---|
| `q<0-1023>;` | Sets digital potentiometer value directly (manual PS control). |
| `r<target_voltage>;` | Runs automatic PS0 regulation loop toward the target voltage. |

## Motion Commands

| Command | What it does |
|---|---|
| `x<steps>;` | Moves X axis by signed step count with limit checking. |
| `y<steps>;` | Moves Y axis by signed step count with limit checking. |
| `z<steps>;` | Moves Z axis by signed step count with limit checking. |
| `Z<steps>;` | Coupled Y+Z move with limit checking; updates logical Y offset compensation. |
| `M<x>,<y>,<z>;` | Sequential move with limits (`X` then `Y` then coupled `Z` behavior). |
| `ux<steps>;` | Unlimited X move (no limit checks). |
| `uy<steps>;` | Unlimited Y move (no limit checks). |
| `uz<steps>;` | Unlimited Z move (no limit checks). |
| `uZ<steps>;` | Unlimited coupled Y+Z move (no limit checks) with logical Y offset compensation. |

## Notes

- Commands are parsed only when terminated by `;`.
- Newline characters are ignored/reset by the parser and are not command terminators.
- Numeric fields accept signed values where applicable (`x-100;`, `M10,-20,5;`, etc.).
