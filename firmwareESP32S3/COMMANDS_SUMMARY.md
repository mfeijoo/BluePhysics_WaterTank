# firmwareESP32S3 Command Summary

All firmware commands are received over serial and must be terminated with a semicolon (`;`).

## General / Status

| Command | What it does |
|---|---|
| `f;` | Queries FRAM startup/programming status and prints the result in human-readable text. |
| `t;` | Reads the MCP9808 temperature sensor and prints temperature in °C. |
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
| `rts;` | Starts continuous binary detector stream with temperature (detector + MCP9808 raw temp bytes). |
| `rte;` | Stops continuous binary detector+temperature stream. |

## Dark Current DAC (AD5675)

| Command | What it does |
|---|---|
| `dc<0|1>,<0-65535>;` | Sets AD5675 dark-current compensation DAC code for channel 0 or 1. Examples: `dc0,3000;`, `dc1,65535;`. |
| `sdc[1-100];` | Runs automatic dark-current setup for both channels: starts each channel at DAC code `0`, measures with 100 samples, increments DAC code by the selected step (`1..100`) while average voltage is above `-10 V`, and stops when average is `<= -10 V` (or max DAC code is reached). `sdc;` defaults to step `10`, while `sdc20;` uses step `20`. During the loop, firmware prints status lines with current code, active channel voltage, and both channel volt/count averages. Sequence runs for ch0 first, then ch1. |

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
