//test
#include <Arduino.h>
#include "driver/pcnt.h"
#include <math.h>
#include <SPI.h>
#include <Wire.h>
#include "Adafruit_MCP9808.h"
#include "Adafruit_FRAM_I2C.h"
#include "ADS1X15.h"

//=======================================
//Temperature create objects
//=======================================

Adafruit_MCP9808 tempsensor = Adafruit_MCP9808();
Adafruit_FRAM_I2C fram = Adafruit_FRAM_I2C();
//ADS1115_WE adc(0x48);F
ADS1115 ADS(0x48);
static bool fram_detected = false;

unsigned int tempbytes;
float temp;

float PSV;
static uint16_t pot_value = 0;
static const float PS_REG_TOLERANCE_V = 0.05f;
static const uint16_t POT_MIN = 0;
static const uint16_t POT_MAX = 1023;

// AD5675 DAC (dark-current offset compensation)
static const uint8_t AD5675_ADDR = 0x0F;
static const uint8_t AD5675_CMD_WRITE_UPDATE = 0x3;
static uint16_t dark_current_code[2] = {0, 0};
#define I2C_SDA_PIN 8
#define I2C_SCL_PIN 9
#define I2C_CLOCK_HZ 100000
#define FRAM_SIMPLE_ADDR MB85RC_DEFAULT_ADDRESS
#define FRAM_OPTIMAL_VOLTAGE_INT_ADDR 0x0000
#define FRAM_OPTIMAL_VOLTAGE_DEC_ADDR 0x0001
#define PSFC 16.1817
#define PSFCind 0.14022
//#define PSFC 1
//#define PSFCind 0


// =================== STEPPER PINS ===================
static const int X_STEP = 18;
static const int X_DIR  = 17;

static const int Y_STEP = 47;
static const int Y_DIR  = 14;

static const int Z_STEP = 10;
static const int Z_DIR  = 3;

// =================== ENCODER PINS (MAX3094E outputs) ===================
static const int X_ENC_A = 4;
static const int X_ENC_B = 5;

static const int Y_ENC_A = 6;
static const int Y_ENC_B = 7;

static const int Z_ENC_A = 15;
static const int Z_ENC_B = 16;

//===========================================================================
// STEPPING SETTINGS
//===========================================================================
static volatile uint32_t STEP_PULSE_US = 800; // STEP high time
static volatile uint32_t STEP_GAP_US   = 800; // STEP low time

//===============================================================================
// PCNT 32-bit extensions settings
//===============================================================================
static const int16_t PCNT_LIMIT = 30000;
static volatile int32_t limmaxpcnt32x = 15000;
static volatile int32_t limminpcnt32x = -15000;
static volatile int32_t limmaxpcnt32y = 15000;
static volatile int32_t limminpcnt32y = -15000;
static volatile int32_t limmaxpcnt32z = 15000;
static volatile int32_t limminpcnt32z = -15000;

//==========================================================
// PCNT 32-bit helper struct (software extension)
//==========================================================
struct Pcnt32 {
  pcnt_unit_t unit;
  pcnt_channel_t ch;
  int pinA;
  int pinB;
  volatile int32_t base; // software extension
};

// One unit per axis
static Pcnt32 pcX {PCNT_UNIT_0, PCNT_CHANNEL_0, X_ENC_A, X_ENC_B};
static Pcnt32 pcY {PCNT_UNIT_1, PCNT_CHANNEL_0, Y_ENC_A, Y_ENC_B};
static Pcnt32 pcZ {PCNT_UNIT_2, PCNT_CHANNEL_0, Z_ENC_A, Z_ENC_B};

//============================================================
// Z logical coordinate offset (so Z comp moves don't change "coord Z")
//============================================================
static volatile int32_t y_offset = 0;

// =================== KINEMATICS / CALIBRATION ===================
static const double STEPS_PER_REV      = 200.0;
static const double ENC_COUNTS_PER_REV = 400.0;
static const double COUNTS_PER_STEP    = ENC_COUNTS_PER_REV / STEPS_PER_REV;

// Error output mode: false = binary packets only, true = human-readable Serial text.
static bool error_messages_human = false;

//===============================================================================
// =================== DETECTOR / SPI SETTINGS ===================
// YOU MUST EDIT THESE PINS TO MATCH YOUR WIRING ON ESP32-S3
//===============================================================================

// SPI pins (set to your wiring)
static const int DET_SCK  = 12;
static const int DET_MISO = 13;
static const int DET_MOSI = 11;

// Chip selects (set to your wiring)
static const int CS_ADQ = 37;
static const int CS_POT = 36;

// Integrator control pins (set to your wiring)
static const int RST_PIN  = 40;
static const int HOLD_PIN = 41;
static const int CAP_SEL_0 = 2;
static const int SERIAL_TIMING_PIN = 21;

// Timing
static volatile uint32_t integraltimemicros = 700; // default 700 us, can set to 200 us
static const uint32_t resettimemicros = 10;

// Device identity (currently hardcoded)
static const char DEVICE_MODEL[] = "model11.2";
static const char DEVICE_FIRMWARE_VERSION[] = "model11.2.01";

// ADS8688A access aligned with test_sketch_Aleix_Cartucho/SPIADC2:
// - SPI mode 0
// - MAN_Ch_n commands (0xC000 for CH0, 0xC400 for CH1)
// - ±2.5*Vref range setup through program registers
static SPISettings detSPI(16000000, MSBFIRST, SPI_MODE0);
static const float ADS8688A_VREF = 4.096f;
static const uint16_t ADS8688A_CMD_MAN_CH0 = 0xC000;
static const uint16_t ADS8688A_CMD_MAN_CH1 = 0xC400;
static uint8_t det_current_channel = 0xFF;

// Raw detector readings (2 channels like your old code)
static volatile uint16_t det_ch0 = 0;
static volatile uint16_t det_ch1 = 0;

// Measurement buffer
struct Sample {
  uint32_t idx;
  uint32_t dt_us;
  uint16_t ch0;
  uint16_t ch1;
};

static const uint32_t MEAS_MAX_SAMPLES     = 5000;  // RAM use ~ (5000 * 8) = 40 KB
static const uint32_t MEAS_DEFAULT_SAMPLES = 1000;  // predefined "period" = samples * integraltimemicros
static Sample measBuf[MEAS_MAX_SAMPLES];
//static uint32_t det_sample_counter = 0;

//======================================================================
// PCNT ISR: extend counter when it hits high/low limit
//======================================================================
static void IRAM_ATTR pcnt_isr(void *arg) {
  Pcnt32 *p = (Pcnt32*)arg;

  uint32_t st = 0;
  pcnt_get_event_status(p->unit, &st);

  if (st & PCNT_EVT_H_LIM) {
    p->base += PCNT_LIMIT;
    pcnt_counter_clear(p->unit);
  }
  if (st & PCNT_EVT_L_LIM) {
    p->base -= PCNT_LIMIT;
    pcnt_counter_clear(p->unit);
  }
}

//=========================================================================
// PCNT setup for quadrature (A/B)
//=========================================================================
static void pcntSetup(Pcnt32 &p) {
  pcnt_config_t c = {};
  c.pulse_gpio_num = p.pinA;
  c.ctrl_gpio_num  = p.pinB;
  c.unit           = p.unit;
  c.channel        = p.ch;

  c.pos_mode = PCNT_COUNT_INC;
  c.neg_mode = PCNT_COUNT_DEC;

  c.lctrl_mode = PCNT_MODE_REVERSE;
  c.hctrl_mode = PCNT_MODE_KEEP;

  c.counter_h_lim = PCNT_LIMIT;
  c.counter_l_lim = -PCNT_LIMIT;

  pcnt_unit_config(&c);

  pcnt_set_filter_value(p.unit, 100);
  pcnt_filter_enable(p.unit);

  pcnt_event_enable(p.unit, PCNT_EVT_H_LIM);
  pcnt_event_enable(p.unit, PCNT_EVT_L_LIM);

  pcnt_counter_pause(p.unit);
  pcnt_counter_clear(p.unit);

  static bool isrInstalled = false;
  if (!isrInstalled) {
    pcnt_isr_service_install(0);
    isrInstalled = true;
  }

  pcnt_isr_handler_add(p.unit, pcnt_isr, (void*)&p);

  p.base = 0;
  pcnt_counter_resume(p.unit);
}

static int32_t pcntRead32(const Pcnt32 &p) {
  int16_t v = 0;
  pcnt_get_counter_value(p.unit, &v);
  return p.base + (int32_t)v;
}

static void pcntZero(Pcnt32 &p) {
  pcnt_counter_pause(p.unit);
  pcnt_counter_clear(p.unit);
  p.base = 0;
  pcnt_counter_resume(p.unit);
}

// Logical Y coordinate (raw y + software offset)
static int32_t yCoord() {
  return pcntRead32(pcY) + y_offset;
}

//============================================================
// Stepper helpers
//============================================================
static void stepPulse(int stepPin) {
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(stepPin, LOW);
  delayMicroseconds(STEP_GAP_US);
}

static void stepPulse2(int stepPin1, int stepPin2) {
  digitalWrite(stepPin1, HIGH);
  digitalWrite(stepPin2, HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(stepPin1, LOW);
  digitalWrite(stepPin2, LOW);
  delayMicroseconds(STEP_GAP_US);
}

static void moveAxisSteps(char axis, int32_t steps) {
  int stepPin = -1, dirPin = -1;

  switch (axis){
    case 'x': stepPin = X_STEP; dirPin = X_DIR; break;
    case 'y': stepPin = Y_STEP; dirPin = Y_DIR; break;
    case 'z': stepPin = Z_STEP; dirPin = Z_DIR; break;
    default: return;
  }

  bool dir = (steps >= 0);
  uint32_t n = (steps >= 0) ? (uint32_t)steps : (uint32_t)(-steps);

  digitalWrite(dirPin, dir ? HIGH : LOW);
  delayMicroseconds(2);

  for (uint32_t i = 0; i < n; i++) stepPulse(stepPin);
}

// True coupled Y+Z: one Y step + one Z step at the same time
static void moveYZCoupledSteps(int32_t steps) {
  bool dir = (steps >= 0);
  uint32_t n = (steps >= 0) ? (uint32_t)steps : (uint32_t)(-steps);

  digitalWrite(Y_DIR, dir ? HIGH : LOW);
  digitalWrite(Z_DIR, dir ? HIGH : LOW);
  delayMicroseconds(2);

  for (uint32_t i = 0; i < n; i++) {
    stepPulse2(Y_STEP, Z_STEP);
  }
}

static bool inLimitRange(double value, int32_t limMin, int32_t limMax) {
  return value >= (double)limMin && value <= (double)limMax;
}

static double stepsToPcnt32Delta(int32_t steps) {
  return (double)steps * COUNTS_PER_STEP;
}

static void sendErr(uint8_t cmd_id, uint8_t err_code);
static void sendPcnt32LimitsPacket();
static void sendStepDelaysPacket();
static void sendIntegrationTimePacket();
static void printIntegrationTimeHuman();
static float detReadAverageAndPrintHuman(uint8_t channel, uint32_t sampleCount, float *averageCountsOut = nullptr, bool printHuman = true);

static uint8_t ad5675_write_update(uint8_t ch, uint16_t code) {
  if (ch > 1) return 0;

  // AD5675 channel mapping in this hardware is inverted:
  // logical ch0 -> DAC channel B, logical ch1 -> DAC channel A.
  // Swap 0/1 here so user-facing commands dc0/dc1 control expected outputs.
  uint8_t hw_ch = (uint8_t)(ch ^ 0x01);

  Wire.beginTransmission(AD5675_ADDR);
  Wire.write((uint8_t)((AD5675_CMD_WRITE_UPDATE << 4) | hw_ch));
  Wire.write((uint8_t)(code >> 8));
  Wire.write((uint8_t)(code & 0xFF));

  uint8_t tx_status = (uint8_t)Wire.endTransmission();
  if (tx_status == 0) dark_current_code[ch] = code;
  return (tx_status == 0) ? 1 : 0;
}

static bool i2cDevicePresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return (Wire.endTransmission() == 0);
}

static bool framRawWriteByte(uint8_t devAddr, uint16_t memAddr, uint8_t value) {
  Wire.beginTransmission(devAddr);
  Wire.write((uint8_t)(memAddr >> 8));
  Wire.write((uint8_t)(memAddr & 0xFF));
  Wire.write(value);
  return (Wire.endTransmission() == 0);
}

static bool framRawReadByte(uint8_t devAddr, uint16_t memAddr, uint8_t &valueOut) {
  Wire.beginTransmission(devAddr);
  Wire.write((uint8_t)(memAddr >> 8));
  Wire.write((uint8_t)(memAddr & 0xFF));
  if (Wire.endTransmission(false) != 0) return false;

  uint8_t n = Wire.requestFrom((int)devAddr, 1);
  if (n != 1 || !Wire.available()) return false;

  valueOut = Wire.read();
  return true;
}

static bool framReadOptimalVoltageBytes(uint8_t &intPart, uint8_t &decimalPart) {
  if (!i2cDevicePresent(FRAM_SIMPLE_ADDR)) return false;
  if (!fram.begin(FRAM_SIMPLE_ADDR, &Wire)) return false;
  intPart = fram.read8(FRAM_OPTIMAL_VOLTAGE_INT_ADDR);
  decimalPart = fram.read8(FRAM_OPTIMAL_VOLTAGE_DEC_ADDR);
  return true;
}

static bool parseVoltageStringToBytes(const char *text, uint8_t &intPartOut, uint8_t &decimalPartOut) {
  if (text == nullptr || text[0] == 0) return false;

  char *end = nullptr;
  unsigned long intPartUL = strtoul(text, &end, 10);
  if (end == text || intPartUL > 255UL) return false;

  uint8_t decimalPart = 0;
  if (*end == 0) {
    intPartOut = (uint8_t)intPartUL;
    decimalPartOut = 0;
    return true;
  }

  if (*end != '.') return false;
  const char *dec = end + 1;
  if (dec[0] < '0' || dec[0] > '9') return false;

  uint8_t d0 = (uint8_t)(dec[0] - '0');
  if (dec[1] == 0) {
    decimalPart = (uint8_t)(d0 * 10); // "42.1" -> 42.10
  } else {
    if (dec[1] < '0' || dec[1] > '9') return false;
    if (dec[2] != 0) return false; // only up to 2 decimals supported
    uint8_t d1 = (uint8_t)(dec[1] - '0');
    decimalPart = (uint8_t)(d0 * 10 + d1);
  }

  intPartOut = (uint8_t)intPartUL;
  decimalPartOut = decimalPart;
  return true;
}

static bool parseLimitValue(char *&p, int32_t &out, bool requireComma) {
  char *end = nullptr;
  long v = strtol(p, &end, 10);
  if (end == p) return false;

  if (requireComma) {
    if (*end != ',') return false;
    p = end + 1;
  } else {
    if (*end != 0) return false;
  }

  out = (int32_t)v;
  return true;
}

static bool trySetPcnt32LimitsFromCommand(char *cmd) {
  // format: lc<xmin>,<xmax>,<ymin>,<ymax>,<zmin>,<zmax>;
  if (cmd[0] != 'l' || cmd[1] != 'c') return false;

  int32_t xmin = 0, xmax = 0;
  int32_t ymin = 0, ymax = 0;
  int32_t zmin = 0, zmax = 0;

  char *p = cmd + 2;
  if (!parseLimitValue(p, xmin, true) ||
      !parseLimitValue(p, xmax, true) ||
      !parseLimitValue(p, ymin, true) ||
      !parseLimitValue(p, ymax, true) ||
      !parseLimitValue(p, zmin, true) ||
      !parseLimitValue(p, zmax, false)) {
    sendErr('c', 0x01);
    return true;
  }

  if (xmin >= xmax || ymin >= ymax || zmin >= zmax) {
    sendErr('c', 0x02);
    return true;
  }

  limminpcnt32x = xmin;
  limmaxpcnt32x = xmax;
  limminpcnt32y = ymin;
  limmaxpcnt32y = ymax;
  limminpcnt32z = zmin;
  limmaxpcnt32z = zmax;

  sendAck('c');
  sendPcnt32LimitsPacket();
  return true;
}

static bool trySetStepDelaysFromCommand(char *cmd) {
  // format: stepdelays<pulse_us>,<gap_us>;
  if (strncmp(cmd, "stepdelays", 10) != 0) return false;

  char *p = cmd + 10;
  char *end = nullptr;

  unsigned long pulse = strtoul(p, &end, 10);
  if (end == p || *end != ',') {
    sendErr('d', 0x01);
    return true;
  }

  p = end + 1;
  unsigned long gap = strtoul(p, &end, 10);
  if (end == p || *end != 0) {
    sendErr('d', 0x01);
    return true;
  }

  if (pulse < 1 || pulse > 1000000UL || gap < 1 || gap > 1000000UL) {
    sendErr('d', 0x02);
    return true;
  }

  STEP_PULSE_US = (uint32_t)pulse;
  STEP_GAP_US = (uint32_t)gap;

  sendAck('d');
  sendStepDelaysPacket();
  return true;
}

static bool checkSingleAxisMoveLimit(char axis, int32_t steps) {
  int32_t current = 0;
  int32_t limMin = 0;
  int32_t limMax = 0;

  switch (axis) {
    case 'x':
      current = pcntRead32(pcX);
      limMin = limminpcnt32x;
      limMax = limmaxpcnt32x;
      break;
    case 'y':
      current = yCoord();
      limMin = limminpcnt32y;
      limMax = limmaxpcnt32y;
      break;
    case 'z':
      current = pcntRead32(pcZ);
      limMin = limminpcnt32z;
      limMax = limmaxpcnt32z;
      break;
    default:
      return false;
  }

  double delta = stepsToPcnt32Delta(steps);
  double projected = (double)current + delta;

  if (!inLimitRange(projected, limMin, limMax)) {
    sendErr((uint8_t)axis, 0x03);
    return false;
  }

  return true;
}

static bool checkCoupledYZMoveLimit(int32_t steps) {
  int32_t currentY = yCoord();
  int32_t currentZ = pcntRead32(pcZ);
  double delta = stepsToPcnt32Delta(steps);

  double projectedY = (double)currentY + delta;
  double projectedZ = (double)currentZ + delta;

  bool yOk = inLimitRange(projectedY, limminpcnt32y, limmaxpcnt32y);
  bool zOk = inLimitRange(projectedZ, limminpcnt32z, limmaxpcnt32z);
  if (yOk && zOk) return true;

  sendErr('Z', 0x03);

  return false;
}

static bool moveXYZSequentialStepsWithLimitCheck(int32_t xSteps, int32_t ySteps, int32_t zSteps) {
  int32_t currentX = pcntRead32(pcX);
  int32_t currentY = yCoord();
  int32_t currentZ = pcntRead32(pcZ);

  double projectedX = (double)currentX + stepsToPcnt32Delta(xSteps);
  double projectedY = (double)currentY + stepsToPcnt32Delta(ySteps);
  double projectedZ = (double)currentZ + stepsToPcnt32Delta(zSteps);

  bool xOk = inLimitRange(projectedX, limminpcnt32x, limmaxpcnt32x);
  bool yOk = inLimitRange(projectedY, limminpcnt32y, limmaxpcnt32y);
  bool zOk = inLimitRange(projectedZ, limminpcnt32z, limmaxpcnt32z);

  if (!xOk || !yOk || !zOk) {
    sendErr('M', 0x03);
    return false;
  }

  moveAxisSteps('x', xSteps);
  moveAxisSteps('y', ySteps);

  int32_t y_before = pcntRead32(pcY);
  moveYZCoupledSteps(zSteps);
  int32_t y_after = pcntRead32(pcY);
  y_offset -= (y_after - y_before);

  sendCoordsPacket(0x21);
  return true;
}


//============================================================
// Serial helpers
//============================================================

//-------Helpers for streaming
unsigned long time_start_streaming = 0;
unsigned long det_stream_last_us = 0;
unsigned long det_sample_counter = 0;
static bool det_human_streaming = false;
static uint32_t det_human_t0_us = 0;
static uint32_t det_human_last_us = 0;
static uint32_t det_human_idx = 0;
static bool det_bytes_streaming = false;
static uint32_t det_bytes_t0_us = 0;
static uint32_t det_bytes_last_us = 0;
static uint32_t det_bytes_idx = 0;
static bool det_pulse_count_streaming = false;
static uint32_t det_pulse_last_us = 0;
static uint32_t det_pulse_t0_us = 0;
static uint32_t det_pulse_idx = 0;
static uint32_t det_pulse_count = 0;
static uint32_t det_pulse_coincide_count = 0;
static bool det_pulse_prev_above_threshold = false;
static float det_pulse_threshold_v = 0.0f;
static float det_pulse_acr = 1.0f;
static float det_pulse_cf = 1.0f;
static double det_pulse_accumulated_dose = 0.0;
static bool det_temp_bytes_streaming = false;
static uint32_t det_temp_bytes_t0_us = 0;
static uint32_t det_temp_bytes_last_us = 0;
static uint32_t det_temp_bytes_idx = 0;
static const uint8_t PKT_STREAM_START = 0x32;
static const uint8_t PKT_STREAM_SAMPLE = 0x33;
static const uint8_t PKT_STREAM_STOP = 0x34;
static const uint8_t PKT_TEMP_STREAM_START = 0x35;
static const uint8_t PKT_TEMP_STREAM_SAMPLE = 0x36;
static const uint8_t PKT_TEMP_STREAM_STOP = 0x37;
static bool sdc_routine_active = false;
static bool sdc_cancel_requested = false;

static bool consumeSdcStopCommandIfPresent() {
  static char cmd[24];
  static size_t idx = 0;

  while (Serial.available()) {
    char c = (char)Serial.read();

    if (c == '\r' || c == '\n') {
      if (idx == 0) continue;
      idx = 0;
      continue;
    }

    if (c == ';') {
      cmd[idx] = 0;
      idx = 0;
      if (strcmp(cmd, "sdcstop") == 0) {
        sdc_cancel_requested = true;
        Serial.println("sdcstop received: stopping sdc/sdcv routine.");
        return true;
      }
      continue;
    }

    if (idx < sizeof(cmd) - 1) cmd[idx++] = c;
    else idx = 0;
  }

  return sdc_cancel_requested;
}

static bool readCmd(char *buf, size_t maxlen) {
  static size_t idx = 0;

  while (Serial.available()) {
    char c = (char)Serial.read();

    // Ignore serial monitor line endings and surrounding whitespace.
    if (c == '\r' || c == '\n') {
      if (idx == 0) continue;
      // If line ending arrives mid-command, reset to avoid poisoning next command.
      idx = 0;
      continue;
    }

    if (c == ';') {
      buf[idx] = 0;
      idx = 0;
      return true;
    }

    if (idx < maxlen - 1) buf[idx++] = c;
    else idx = 0; // overflow -> reset
  }
  return false;
}

static void sendPktHeader(uint8_t type) {
  Serial.write(0xAA);
  Serial.write(0x55);
  Serial.write(type);
}

static void sendAck(uint8_t cmd_id) {
  sendPktHeader(0x10);
  Serial.write(cmd_id);
}

static void sendErr(uint8_t cmd_id, uint8_t err_code) {
  if (error_messages_human) {
    Serial.print("ERR cmd=");
    Serial.print((char)cmd_id);
    Serial.print(" code=");
    Serial.println((int)err_code);
    return;
  }

  sendPktHeader(0x11);
  Serial.write(cmd_id);
  Serial.write(err_code);
}

static void sendCoordsPacket(uint8_t type) {
  int32_t x = pcntRead32(pcX);
  int32_t y = yCoord();
  int32_t z = pcntRead32(pcZ);

  sendPktHeader(type);
  Serial.write((uint8_t*)&x, 4);
  Serial.write((uint8_t*)&y, 4);
  Serial.write((uint8_t*)&z, 4);
}

static void sendPcnt32LimitsPacket() {
  int32_t xmin = limminpcnt32x;
  int32_t xmax = limmaxpcnt32x;
  int32_t ymin = limminpcnt32y;
  int32_t ymax = limmaxpcnt32y;
  int32_t zmin = limminpcnt32z;
  int32_t zmax = limmaxpcnt32z;

  sendPktHeader(0x23);
  Serial.write((uint8_t*)&xmin, 4);
  Serial.write((uint8_t*)&xmax, 4);
  Serial.write((uint8_t*)&ymin, 4);
  Serial.write((uint8_t*)&ymax, 4);
  Serial.write((uint8_t*)&zmin, 4);
  Serial.write((uint8_t*)&zmax, 4);
}

static void sendStepDelaysPacket() {
  uint32_t pulse = STEP_PULSE_US;
  uint32_t gap = STEP_GAP_US;

  sendPktHeader(0x24);
  Serial.write((uint8_t*)&pulse, 4);
  Serial.write((uint8_t*)&gap, 4);
}

static void sendIntegrationTimePacket() {
  uint32_t integ = (uint32_t)integraltimemicros;
  sendPktHeader(0x25);
  Serial.write((uint8_t*)&integ, 4);
}

static void printPcnt32ValuesHuman() {
  int32_t x = pcntRead32(pcX);
  int32_t y = yCoord();
  int32_t z = pcntRead32(pcZ);

  Serial.print("pcnt32 X: ");
  Serial.println(x);
  Serial.print("pcnt32 Y: ");
  Serial.println(y);
  Serial.print("pcnt32 Z: ");
  Serial.println(z);
}

static void printPcnt32LimitsHuman() {
  Serial.println("pcnt32 limits:");

  Serial.print("X min: ");
  Serial.print(limminpcnt32x);
  Serial.print(", X max: ");
  Serial.println(limmaxpcnt32x);

  Serial.print("Y min: ");
  Serial.print(limminpcnt32y);
  Serial.print(", Y max: ");
  Serial.println(limmaxpcnt32y);

  Serial.print("Z min: ");
  Serial.print(limminpcnt32z);
  Serial.print(", Z max: ");
  Serial.println(limmaxpcnt32z);
}

static void printStepDelaysHuman() {
  Serial.print("STEP_PULSE_US: ");
  Serial.println(STEP_PULSE_US);
  Serial.print("STEP_GAP_US: ");
  Serial.println(STEP_GAP_US);
}

static void printIntegrationTimeHuman() {
  Serial.print("Integration time (us): ");
  Serial.println((uint32_t)integraltimemicros);
}

static void printDeviceInfoHuman() {
  Serial.print("Model: ");
  Serial.println(DEVICE_MODEL);
  Serial.print("Firmware version: ");
  Serial.println(DEVICE_FIRMWARE_VERSION);
}

static void detWriteProgramRegister(uint8_t addr, uint8_t data) {
  // 16-bit command = [ADDR(7b) | WR(1b=1) | DATA(8b)] + 8 extra clocks
  // (same sequence used in test sketch SPIADC2 driver)
  uint16_t cmd = (static_cast<uint16_t>(addr) << 9) | (1u << 8) | data;

  SPI.beginTransaction(detSPI);
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer16(cmd);
  SPI.transfer(0x00);
  digitalWrite(CS_ADQ, HIGH);
  SPI.endTransaction();
}

static uint16_t detReadRawChannel(uint8_t channel) {
  uint16_t cmd = (channel == 1) ? ADS8688A_CMD_MAN_CH1 : ADS8688A_CMD_MAN_CH0;

  // ADS8688A has one-frame pipeline in MAN_Ch_n mode:
  // on channel change, send one service frame and discard the reading.
  if (det_current_channel != channel) {
    SPI.beginTransaction(detSPI);
    digitalWrite(CS_ADQ, LOW);
    SPI.transfer16(cmd);
    SPI.transfer16(0x0000);
    digitalWrite(CS_ADQ, HIGH);
    SPI.endTransaction();
    det_current_channel = channel;
  }

  SPI.beginTransaction(detSPI);
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer16(cmd);
  uint16_t raw = SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  SPI.endTransaction();

  return raw;
}

static void detReadChannels() {
  det_ch0 = detReadRawChannel(0);
  det_ch1 = detReadRawChannel(1);
}

static void setPot(uint16_t value) {
  SPI.beginTransaction(SPISettings(7000000, MSBFIRST, SPI_MODE0));

  digitalWrite(CS_POT, LOW);
  SPI.transfer(0x01);
  SPI.transfer16(value << 6);
  digitalWrite(CS_POT, HIGH);

  SPI.endTransaction();
}

// Select integrator capacitor using CAP_SEL_0 only.
// CAP_SEL_0 LOW  -> internal capacitor selected.
// CAP_SEL_0 HIGH -> external capacitor selected.
static void selectCapacitor(bool externalCap) {
  digitalWrite(CAP_SEL_0, externalCap ? HIGH : LOW);
}

static void printCapacitorSelectionHuman() {
  int capSelState = digitalRead(CAP_SEL_0);

  Serial.print("Capacitor selection: ");
  if (capSelState == HIGH) {
    Serial.println("external (CAP_SEL_0=HIGH)");
  } else {
    Serial.println("internal (CAP_SEL_0=LOW)");
  }
}

// One integration sample: HOLD high -> read -> reset -> HOLD low
static void detReadOnce() {
  digitalWrite(HOLD_PIN, HIGH);
  detReadChannels();

  digitalWrite(RST_PIN, LOW);
  delayMicroseconds(resettimemicros);
  digitalWrite(RST_PIN, HIGH);

  delayMicroseconds(10);
  digitalWrite(HOLD_PIN, LOW);
}

static float detCountsToVolts(float counts) {
  // Same conversion used in test_sketch_Aleix_Cartucho/SPIADC2.cpp:
  // V = (code - 32768) * (FSR / 65536), where FSR = 5 * Vref (±2.5*Vref)
  // Sign inverted so detector light pulses are reported as positive voltage.
  const float fsr = 5.0f * ADS8688A_VREF;
  return -((counts - 32768.0f) * (fsr / 65536.0f));
}

static float detReadAverageAndPrintHuman(uint8_t channel, uint32_t sampleCount, float *averageCountsOut, bool printHuman) {
  if (channel > 1) {
    Serial.println("Error: channel must be 0 or 1.");
    return NAN;
  }

  if (sampleCount == 0) {
    Serial.println("Error: sample count must be > 0.");
    return NAN;
  }

  if (sampleCount > MEAS_MAX_SAMPLES) {
    Serial.print("Warning: sample count limited to ");
    Serial.println(MEAS_MAX_SAMPLES);
    sampleCount = MEAS_MAX_SAMPLES;
  }

  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  uint64_t sum = 0;
  uint32_t starttime = micros();
  uint32_t i = 0;
  while (i < sampleCount) {
    if (sdc_routine_active && consumeSdcStopCommandIfPresent()) {
      return NAN;
    }
    if ((uint32_t)(micros() - starttime) >= (uint32_t)integraltimemicros) {
      detReadOnce();
      starttime = micros();

      sum += (channel == 0) ? det_ch0 : det_ch1;
      i++;
    }
  }

  float averageCounts = (float)sum / (float)sampleCount;
  float averageVolts = detCountsToVolts(averageCounts);
  if (averageCountsOut != nullptr) *averageCountsOut = averageCounts;

  if (printHuman) {
    Serial.print("Detector average ch");
    Serial.print((int)channel);
    Serial.print(" from ");
    Serial.print(sampleCount);
    Serial.print(" samples: ");
    Serial.print(averageVolts, 6);
    Serial.print(" V (");
    Serial.print(averageCounts, 3);
    Serial.println(" counts)");
  }

  return averageVolts;
}

static bool setDarkCurrentChannelToTarget(uint8_t ch, float targetVolts, uint32_t sampleCount, uint16_t codeStep) {
  if (ch > 1) return false;
  if (sampleCount == 0) sampleCount = 100;
  if (codeStep == 0) codeStep = 1;

  uint16_t code = 0;
  if (!ad5675_write_update(ch, code)) {
    Serial.println("Error: AD5675 I2C write failed while setting initial code.");
    return false;
  }

  while (true) {
    if (consumeSdcStopCommandIfPresent()) return false;

    float ch0Counts = 0.0f;
    float ch1Counts = 0.0f;
    float ch0Volts = detReadAverageAndPrintHuman(0, sampleCount, &ch0Counts, false);
    float ch1Volts = detReadAverageAndPrintHuman(1, sampleCount, &ch1Counts, false);
    if (isnan(ch0Volts) || isnan(ch1Volts)) return false;

    float activeVolts = (ch == 0) ? ch0Volts : ch1Volts;
    Serial.print("sdc status: tuning ch");
    Serial.print((int)ch);
    Serial.print(", code=");
    Serial.print((int)code);
    Serial.print(", activeV=");
    Serial.print(activeVolts, 6);
    Serial.print(" V, ch0=");
    Serial.print(ch0Volts, 6);
    Serial.print(" V (");
    Serial.print(ch0Counts, 3);
    Serial.print(" counts), ch1=");
    Serial.print(ch1Volts, 6);
    Serial.print(" V (");
    Serial.print(ch1Counts, 3);
    Serial.println(" counts)");

    if (activeVolts <= targetVolts) return true;

    if (code == 65535) {
      Serial.print("Warning: dark current ch");
      Serial.print((int)ch);
      Serial.println(" reached max DAC code before target voltage.");
      return false;
    }

    uint32_t nextCode = (uint32_t)code + (uint32_t)codeStep;
    if (nextCode > 65535U) nextCode = 65535U;
    code = (uint16_t)nextCode;
    if (!ad5675_write_update(ch, code)) {
      Serial.println("Error: AD5675 I2C write failed during dark current regulation.");
      return false;
    }
  }
}

static bool setDarkCurrentToZeroVolts(uint16_t codeStep) {
  sdc_routine_active = true;
  sdc_cancel_requested = false;
  Serial.print("Set dark current routine: target <= 0.0 V, samples=100, codeStep=");
  Serial.println((int)codeStep);

  if (!setDarkCurrentChannelToTarget(0, 0.0f, 100, codeStep)) {
    sdc_routine_active = false;
    return false;
  }
  if (!setDarkCurrentChannelToTarget(1, 0.0f, 100, codeStep)) {
    sdc_routine_active = false;
    return false;
  }

  sdc_routine_active = false;
  Serial.println("Set dark current routine completed.");
  return true;
}

static bool setDarkCurrentToTargetVoltage(float targetVolts, uint16_t codeStep) {
  sdc_routine_active = true;
  sdc_cancel_requested = false;
  Serial.print("Set dark current routine: target <= ");
  Serial.print(targetVolts, 4);
  Serial.print(" V, samples=100, codeStep=");
  Serial.println((int)codeStep);

  if (!setDarkCurrentChannelToTarget(0, targetVolts, 100, codeStep)) {
    sdc_routine_active = false;
    return false;
  }
  if (!setDarkCurrentChannelToTarget(1, targetVolts, 100, codeStep)) {
    sdc_routine_active = false;
    return false;
  }

  sdc_routine_active = false;
  Serial.println("Set dark current routine completed.");
  return true;
}


static void detReadAndPrintHuman(uint32_t N) {
  if (N == 0) {
    Serial.println("Error: readN requires N > 0");
    return;
  }

  if (N > MEAS_MAX_SAMPLES) {
    Serial.print("Warning: N limited to ");
    Serial.println(MEAS_MAX_SAMPLES);
    N = MEAS_MAX_SAMPLES;
  }

  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  uint32_t starttime = micros();
  uint32_t i = 0;
  while (i < N) {
    if ((uint32_t)(micros() - starttime) >= (uint32_t)integraltimemicros) {
      detReadOnce();
      starttime = micros();

      measBuf[i].idx = i;
      measBuf[i].ch0 = det_ch0;
      measBuf[i].ch1 = det_ch1;
      i++;
    }
  }

  Serial.println("Detector read results:");
  for (uint32_t j = 0; j < N; j++) {
    float det_ch0_volts = detCountsToVolts(measBuf[j].ch0);
    float det_ch1_volts = detCountsToVolts(measBuf[j].ch1);
    Serial.print("read ");
    Serial.print(measBuf[j].idx);
    Serial.print(": ch0=");
    Serial.print(measBuf[j].ch0);
    Serial.print(", ch1=");
    Serial.print(measBuf[j].ch1);
    Serial.print(" counts");
    Serial.print(det_ch0_volts, 6);
    Serial.print(" V ");
    Serial.print(det_ch1_volts, 6);
    Serial.println(" V");
  }
}

static void detReadAndPrintHumanStart() {
  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  det_human_t0_us = micros();
  det_human_last_us = det_human_t0_us;
  det_human_idx = 0;
  det_human_streaming = true;
  det_bytes_streaming = false;
  det_temp_bytes_streaming = false;

  Serial.println("Detector streaming started (idx, dt_us, ch0, ch1)");
}

static void detReadAndPrintHumanStop() {
  det_human_streaming = false;
  Serial.println("Detector streaming stopped");
}

static void detReadAndPrintHumanService() {
  if (!det_human_streaming) return;

  uint32_t now = micros();
  if ((uint32_t)(now - det_human_last_us) < (uint32_t)integraltimemicros) return;

  detReadOnce();
  now = micros();
  det_human_last_us = now;

  Serial.print(det_human_idx);
  Serial.print(", ");
  Serial.print((uint32_t)(now - det_human_t0_us));
  Serial.print(", ");
  Serial.print(det_ch0);
  Serial.print(", ");
  Serial.println(det_ch1);
  det_human_idx++;
}

static void detReadAndSendBytesStart() {
  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  det_bytes_t0_us = micros();
  det_bytes_last_us = det_bytes_t0_us;
  det_bytes_idx = 0;
  det_bytes_streaming = true;
  det_pulse_count_streaming = false;
  det_human_streaming = false;
  det_temp_bytes_streaming = false;

  sendAck('s');
  sendPktHeader(PKT_STREAM_START);
  uint32_t integ = (uint32_t)integraltimemicros;
  Serial.write((uint8_t*)&integ, 4);
}

static void detReadAndSendBytesStop() {
  det_bytes_streaming = false;

  sendAck('e');
  sendPktHeader(PKT_STREAM_STOP);
  Serial.write((uint8_t*)&det_bytes_idx, 4);
}

//This function takes only 80 microseconds to send the info via serial
//measured with osciloscope
static void detReadAndSendBytesService() {
  if (!det_bytes_streaming) return;

  uint32_t now = micros();
  if ((uint32_t)(now - det_bytes_last_us) < (uint32_t)integraltimemicros) return;

  detReadOnce();
  now = micros();
  det_bytes_last_us = now;

  digitalWrite(SERIAL_TIMING_PIN, HIGH);
  sendPktHeader(PKT_STREAM_SAMPLE);
  Serial.write((uint8_t*)&det_bytes_idx, 4);
  uint32_t dt = (uint32_t)(now - det_bytes_t0_us);
  Serial.write((uint8_t*)&dt, 4);
  Serial.write((uint8_t*)&det_ch0, 2);
  Serial.write((uint8_t*)&det_ch1, 2);
  digitalWrite(SERIAL_TIMING_PIN, LOW);
  det_bytes_idx++;
}

static void detReadAndSendBytesWithTempStart() {
  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  det_temp_bytes_t0_us = micros();
  det_temp_bytes_last_us = det_temp_bytes_t0_us;
  det_temp_bytes_idx = 0;
  det_temp_bytes_streaming = true;
  det_bytes_streaming = false;
  det_pulse_count_streaming = false;
  det_human_streaming = false;

  sendAck('T');
  sendPktHeader(PKT_TEMP_STREAM_START);
  uint32_t integ = (uint32_t)integraltimemicros;
  Serial.write((uint8_t*)&integ, 4);
}

static void detReadAndSendBytesWithTempStop() {
  det_temp_bytes_streaming = false;

  sendAck('U');
  sendPktHeader(PKT_TEMP_STREAM_STOP);
  Serial.write((uint8_t*)&det_temp_bytes_idx, 4);
}

//This function takes almost 700 micro seconds to execute
//to measure the temp takes a long time
//measured with osciloscope
static void detReadAndSendBytesWithTempService() {
  if (!det_temp_bytes_streaming) return;

  uint32_t now = micros();
  if ((uint32_t)(now - det_temp_bytes_last_us) < (uint32_t)integraltimemicros) return;

  detReadOnce();
  now = micros();
  det_temp_bytes_last_us = now;

  digitalWrite(SERIAL_TIMING_PIN, HIGH);
  uint32_t temp_start_us = micros();
  uint16_t temp_raw = tempsensor.read16(0x05);
  //uint16_t temp_raw = 32;
  uint32_t temp_read_us = (uint32_t)(micros() - temp_start_us);

  sendPktHeader(PKT_TEMP_STREAM_SAMPLE);
  Serial.write((uint8_t*)&det_temp_bytes_idx, 4);
  uint32_t dt = (uint32_t)(now - det_temp_bytes_t0_us);
  Serial.write((uint8_t*)&dt, 4);
  Serial.write((uint8_t*)&det_ch0, 2);
  Serial.write((uint8_t*)&det_ch1, 2);
  Serial.write((uint8_t*)&temp_raw, 2);
  Serial.write((uint8_t*)&temp_read_us, 4);
  digitalWrite(SERIAL_TIMING_PIN, LOW);

  det_temp_bytes_idx++;
}

static void detReadAndCountPulsesStart(float thresholdVolts, float acr, float cf) {
  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  det_pulse_last_us = micros();
  det_pulse_t0_us = det_pulse_last_us;
  det_pulse_idx = 0;
  det_pulse_count = 0;
  det_pulse_coincide_count = 0;
  det_pulse_prev_above_threshold = false;
  det_pulse_threshold_v = thresholdVolts;
  det_pulse_acr = acr;
  det_pulse_cf = cf;
  det_pulse_accumulated_dose = 0.0;
  det_pulse_count_streaming = true;
  det_bytes_streaming = false;
  det_human_streaming = false;
  det_temp_bytes_streaming = false;

  // Keep stream packet format identical to rs;/re;
  sendAck('s');
  sendPktHeader(PKT_STREAM_START);
  uint32_t integ = (uint32_t)integraltimemicros;
  Serial.write((uint8_t*)&integ, 4);

  Serial.print("Pulse counting started on ch0 with threshold ");
  Serial.print(det_pulse_threshold_v, 6);
  Serial.print(" V, ACR=");
  Serial.print(det_pulse_acr, 6);
  Serial.print(", CF=");
  Serial.println(det_pulse_cf, 6);
}

static void detReadAndCountPulsesStopAndPrint() {
  det_pulse_count_streaming = false;

  // Keep stream packet format identical to rs;/re;
  sendAck('e');
  sendPktHeader(PKT_STREAM_STOP);
  Serial.write((uint8_t*)&det_pulse_idx, 4);

  Serial.print("Pulse counting stopped. Total pulses on ch0: ");
  Serial.println(det_pulse_count);
  Serial.print("Total coincide pulses on ch0: ");
  Serial.println(det_pulse_coincide_count);
  Serial.print("Total accumulated dose: ");
  Serial.println((float)det_pulse_accumulated_dose, 6);
}

static void detReadAndCountPulsesService() {
  if (!det_pulse_count_streaming) return;

  uint32_t now = micros();
  if ((uint32_t)(now - det_pulse_last_us) < (uint32_t)integraltimemicros) return;

  detReadOnce();
  det_pulse_last_us = micros();

  sendPktHeader(PKT_STREAM_SAMPLE);
  Serial.write((uint8_t*)&det_pulse_idx, 4);
  uint32_t dt = (uint32_t)(det_pulse_last_us - det_pulse_t0_us);
  Serial.write((uint8_t*)&dt, 4);
  Serial.write((uint8_t*)&det_ch0, 2);
  Serial.write((uint8_t*)&det_ch1, 2);
  det_pulse_idx++;

  float det_ch0_volts = detCountsToVolts(det_ch0);
  float det_ch1_volts = detCountsToVolts(det_ch1);
  float dose_sample = (det_ch0_volts - (det_ch1_volts * det_pulse_acr)) * det_pulse_cf;
  det_pulse_accumulated_dose += (double)dose_sample;

  bool aboveThreshold = (det_ch0_volts > det_pulse_threshold_v);
  if (aboveThreshold && !det_pulse_prev_above_threshold) {
    det_pulse_count++;
  } else if (aboveThreshold && det_pulse_prev_above_threshold) {
    det_pulse_coincide_count++;
  }
  det_pulse_prev_above_threshold = aboveThreshold;
}

static void detReadAndSendBytes(uint32_t N) {
  if (N == 0) {
    sendErr('r', 0x01);
    return;
  }

  if (N > MEAS_MAX_SAMPLES) {
    N = MEAS_MAX_SAMPLES;
  }

  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  uint32_t t0 = micros();
  uint32_t starttime = t0;
  uint32_t i = 0;
  while (i < N) {
    if ((uint32_t)(micros() - starttime) >= (uint32_t)integraltimemicros) {
      detReadOnce();
      uint32_t now = micros();
      starttime = now;

      measBuf[i].idx = i;
      measBuf[i].dt_us = (uint32_t)(now - t0);
      measBuf[i].ch0 = det_ch0;
      measBuf[i].ch1 = det_ch1;
      i++;
    }
  }

  sendAck('r');
  sendPktHeader(0x31);
  Serial.write((uint8_t*)&N, 4);

  uint32_t integ = (uint32_t)integraltimemicros;
  Serial.write((uint8_t*)&integ, 4);

  Serial.write((uint8_t*)measBuf, N * sizeof(Sample));
}

static void readPS() {
  int16_t val_0 = ADS.readADC(0);
  float f = ADS.toVoltage(1); // voltage factor
  PSV = (val_0 * f) * PSFC + PSFCind;
}

static void printPSRegulationStatus(float targetV) {
  Serial.print("PS regulation -> target: ");
  Serial.print(targetV, 2);
  Serial.print(" V, current: ");
  Serial.print(PSV, 4);
  Serial.print(" V, pot: ");
  Serial.println(pot_value);
}

static void regulatePS(float targetV) {
  if (targetV < 0.0f) {
    Serial.println("Error: target PS0 must be >= 0 V");
    return;
  }

  const uint16_t maxIterations = 3000;
  readPS();
  printPSRegulationStatus(targetV);

  for (uint16_t iter = 0; iter < maxIterations; ++iter) {
    float errorV = targetV - PSV;
    if (fabsf(errorV) <= PS_REG_TOLERANCE_V) {
      Serial.println("PS regulation completed within tolerance (+/-0.05 V)");
      return;
    }

    uint16_t step = (uint16_t)fabsf(errorV * 8.0f);
    if (step < 1) step = 1;
    if (step > 20) step = 20;

    if (errorV > 0.0f) {
      if (pot_value >= POT_MAX) {
        Serial.println("PS regulation stopped: pot reached maximum (1023)");
        return;
      }
      if ((uint32_t)pot_value + step > POT_MAX) {
        pot_value = POT_MAX;
      } else {
        pot_value += step;
      }
    } else {
      if (pot_value <= POT_MIN) {
        Serial.println("PS regulation stopped: pot reached minimum (0)");
        return;
      }
      if (pot_value < step) {
        pot_value = POT_MIN;
      } else {
        pot_value -= step;
      }
    }

    setPot(pot_value);
    delay(500);
    readPS();
    printPSRegulationStatus(targetV);
  }

  Serial.println("PS regulation stopped: maximum iterations reached");
}

//============================================================
// Arduino setup/loop
//============================================================
void setup() {
  Serial.begin(921600);
  delay(200);

  pinMode(X_STEP, OUTPUT); pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT); pinMode(Y_DIR, OUTPUT);
  pinMode(Z_STEP, OUTPUT); pinMode(Z_DIR, OUTPUT);

  digitalWrite(X_STEP, LOW);
  digitalWrite(Y_STEP, LOW);
  digitalWrite(Z_STEP, LOW);

  pcntSetup(pcX);
  pcntSetup(pcY);
  pcntSetup(pcZ);

  y_offset = 0;

  // Detector pins
  pinMode(CS_ADQ, OUTPUT);
  digitalWrite(CS_ADQ, HIGH);

  pinMode(CS_POT, OUTPUT);
  digitalWrite(CS_POT, HIGH);

  pinMode(RST_PIN, OUTPUT);
  pinMode(HOLD_PIN, OUTPUT);
  pinMode(CAP_SEL_0, OUTPUT);
  pinMode(SERIAL_TIMING_PIN, OUTPUT);
  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);
  digitalWrite(SERIAL_TIMING_PIN, LOW);

  // Default capacitor selection on startup: internal capacitor.
  selectCapacitor(false);

  // SPI
  SPI.begin(DET_SCK, DET_MISO, DET_MOSI);

  // ADS8688A range setup copied from test sketch approach:
  // Range_CHn register 0x00 => ±2.5 * Vref (max bipolar range).
  for (uint8_t reg = 0x05; reg <= 0x0C; ++reg) {
    detWriteProgramRegister(reg, 0x00);
  }

  ADS.begin();
  ADS.setGain(0);

  // Keep I2C configuration aligned with test_sketch_Aleix_Cartucho.
  // Re-apply after ADS.begin() in case the ADS library re-initializes Wire.
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);

  fram_detected = fram.begin(MB85RC_DEFAULT_ADDRESS, &Wire);

  //Temperature sensor setup
  tempsensor.begin(0x18, &Wire);
  tempsensor.setResolution(3); //this line on
  // Mode Resolution SampleTime
  //  0    0.5°C       30 ms
  //  1    0.25°C      65 ms
  //  2    0.125°C     130 ms
  //  3    0.0625°C    250 ms
  tempsensor.wake(); //this line on
  Serial.println("Temp Sensor ready");

  //Set the PS to 30V at start up
  //regulatePS(30.0);

}


void loop() {
  char cmd[96];

  detReadAndPrintHumanService();
  detReadAndSendBytesService();
  detReadAndSendBytesWithTempService();
  detReadAndCountPulsesService();

  if (!readCmd(cmd, sizeof(cmd))) return;
  if (cmd[0] == 0) return;

  //measure temperature manually
  if (cmd[0] == 't' && cmd[1] == 0) {
    sendAck('t');
    Serial.println("Measuring temperature:");
    temp = tempsensor.readTempC();
    Serial.print(temp);
    Serial.println(" C");
    delay(500);
    //tempbytes = tempsensor.read16(0x05);
    //Serial.write(0xAA);
    //Serial.write(0x55);
    //Serial.write((uint8_t*)&tempbytes, 2);
    return;
  }

  //-----check FRAM I2C presence: fram;
  if (strcmp(cmd, "fram") == 0) {
    // Ensure FRAM probe uses the same explicit I2C bus config as setup.
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    const uint8_t fram_addr0 = MB85RC_DEFAULT_ADDRESS;      // usually 0x50
    const uint8_t fram_addr1 = MB85RC_DEFAULT_ADDRESS + 1;  // usually 0x51

    bool ack0 = i2cDevicePresent(fram_addr0);
    bool ack1 = i2cDevicePresent(fram_addr1);
    uint8_t selected_addr = 0;
    fram_detected = false;

    if (ack0 && fram.begin(fram_addr0, &Wire)) {
      fram_detected = true;
      selected_addr = fram_addr0;
    } else if (ack1 && fram.begin(fram_addr1, &Wire)) {
      fram_detected = true;
      selected_addr = fram_addr1;
    }

    uint16_t manufacturerID = 0;
    uint16_t productID = 0;
    if (fram_detected) {
      fram.getDeviceID(&manufacturerID, &productID);
      Serial.printf("FRAM detected at 0x%02X. Manufacturer ID: 0x%04X, Product ID: 0x%04X\n",
                    selected_addr, manufacturerID, productID);
    } else if (ack0 || ack1) {
      Serial.printf("FRAM detected by I2C ACK (0x%02X=%d, 0x%02X=%d).\n",
                    fram_addr0, ack0 ? 1 : 0, fram_addr1, ack1 ? 1 : 0);
      Serial.println("Note: FRAM library init failed, so Manufacturer/Product ID is unavailable.");
    } else {
      Serial.println("FRAM not detected.");
    }
    return;
  }

  //-----simple FRAM presence check on fixed device 0x50: fram50;
  if (strcmp(cmd, "fram50") == 0) {
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (i2cDevicePresent(FRAM_SIMPLE_ADDR)) {
      Serial.printf("FRAM 0x%02X detected.\n", FRAM_SIMPLE_ADDR);
    } else {
      Serial.printf("FRAM 0x%02X not detected.\n", FRAM_SIMPLE_ADDR);
    }
    return;
  }

  //-----simple FRAM write on fixed device 0x50: fw50<mem_addr>,<value>;
  // examples: fw500,123;  fw50256,171;  (hex accepted too, e.g. fw500x0100,0xAB;)
  if (strncmp(cmd, "fw50", 4) == 0) {
    char *p = cmd + 4;
    char *end = nullptr;

    unsigned long memAddrUL = strtoul(p, &end, 0);
    if (end == p || *end != ',') {
      Serial.println("Error: malformed fw50. Use fw50<mem_addr>,<value>;");
      return;
    }

    p = end + 1;
    unsigned long valueUL = strtoul(p, &end, 0);
    if (end == p || *end != 0) {
      Serial.println("Error: malformed fw50. Use fw50<mem_addr>,<value>;");
      return;
    }

    if (memAddrUL > 0xFFFF || valueUL > 0xFF) {
      Serial.println("Error: fw50 out of range. mem_addr<=0xFFFF, value<=0xFF.");
      return;
    }

    uint16_t memAddr = (uint16_t)memAddrUL;
    uint8_t value = (uint8_t)valueUL;

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!framRawWriteByte(FRAM_SIMPLE_ADDR, memAddr, value)) {
      Serial.printf("FRAM 0x%02X write failed at mem 0x%04X\n", FRAM_SIMPLE_ADDR, memAddr);
      return;
    }

    Serial.printf("FRAM 0x%02X write OK: mem 0x%04X <= 0x%02X\n",
                  FRAM_SIMPLE_ADDR, memAddr, value);
    return;
  }

  //-----FRAM check for first two bytes (0x0000, 0x0001): fcheck50;
  // reads integer/decimal bytes used for optimal voltage storage.
  if (strcmp(cmd, "fcheck50") == 0) {
    uint8_t intByte = 0;
    uint8_t decByte = 0;

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!framReadOptimalVoltageBytes(intByte, decByte)) {
      Serial.printf("FRAM 0x%02X check failed while reading 0x%04X/0x%04X.\n",
                    FRAM_SIMPLE_ADDR, FRAM_OPTIMAL_VOLTAGE_INT_ADDR, FRAM_OPTIMAL_VOLTAGE_DEC_ADDR);
      return;
    }

    bool looksValid = (decByte <= 99);
    Serial.printf("FRAM 0x%02X check: [0x%04X]=0x%02X (%u), [0x%04X]=0x%02X (%u)\n",
                  FRAM_SIMPLE_ADDR,
                  FRAM_OPTIMAL_VOLTAGE_INT_ADDR, intByte, intByte,
                  FRAM_OPTIMAL_VOLTAGE_DEC_ADDR, decByte, decByte);
    Serial.printf("Stored optimal voltage looks %s (decimal byte must be 0..99).\n",
                  looksValid ? "VALID" : "INVALID");
    return;
  }

  //-----store optimal voltage in FRAM 0x50 addresses 0x0000 and 0x0001: ovset<voltage>;
  // example: ovset42.10;
  if (strncmp(cmd, "ovset", 5) == 0) {
    char *p = cmd + 5;
    uint8_t reqInt = 0;
    uint8_t reqDec = 0;
    if (!parseVoltageStringToBytes(p, reqInt, reqDec)) {
      Serial.println("Error: malformed ovset. Use ovset<voltage>; (0..255 with 0..2 decimals, e.g. ovset42.10;)");
      return;
    }

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!i2cDevicePresent(FRAM_SIMPLE_ADDR) || !fram.begin(FRAM_SIMPLE_ADDR, &Wire)) {
      Serial.printf("FRAM 0x%02X write failed for optimal voltage.\n", FRAM_SIMPLE_ADDR);
      return;
    }
    fram.write8(FRAM_OPTIMAL_VOLTAGE_INT_ADDR, reqInt);
    fram.write8(FRAM_OPTIMAL_VOLTAGE_DEC_ADDR, reqDec);

    uint8_t intByte = 0;
    uint8_t decByte = 0;
    if (!framReadOptimalVoltageBytes(intByte, decByte)) {
      Serial.printf("FRAM 0x%02X verify read failed after ovset.\n", FRAM_SIMPLE_ADDR);
      return;
    }

    bool verified = (intByte == reqInt && decByte == reqDec);
    Serial.printf("Optimal voltage save %s: requested %u.%02u V, stored %u.%02u V -> FRAM [0x%04X]=%u, [0x%04X]=%u\n",
                  verified ? "OK" : "MISMATCH",
                  reqInt, reqDec, intByte, decByte,
                  FRAM_OPTIMAL_VOLTAGE_INT_ADDR, intByte,
                  FRAM_OPTIMAL_VOLTAGE_DEC_ADDR, decByte);
    return;
  }

  //-----read and print optimal voltage stored in FRAM 0x50: ovread;
  if (strcmp(cmd, "ovread") == 0) {
    uint8_t intByte = 0;
    uint8_t decByte = 0;

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!framReadOptimalVoltageBytes(intByte, decByte)) {
      Serial.printf("FRAM 0x%02X read failed for optimal voltage.\n", FRAM_SIMPLE_ADDR);
      return;
    }

    float voltage = (float)intByte + ((float)decByte / 100.0f);
    Serial.printf("Optimal voltage (FRAM 0x%02X): %u.%02u V (%.2f V)\n",
                  FRAM_SIMPLE_ADDR, intByte, decByte, voltage);
    if (decByte > 99) {
      Serial.println("Warning: decimal byte is outside expected range (0..99).");
    }
    return;
  }

  //-----simple FRAM read on fixed device 0x50: fr50<mem_addr>;
  // examples: fr500;  fr50256;  (hex accepted too, e.g. fr500x0100;)
  if (strncmp(cmd, "fr50", 4) == 0) {
    char *p = cmd + 4;
    char *end = nullptr;

    unsigned long memAddrUL = strtoul(p, &end, 0);
    if (end == p || *end != 0) {
      Serial.println("Error: malformed fr50. Use fr50<mem_addr>;");
      return;
    }

    if (memAddrUL > 0xFFFF) {
      Serial.println("Error: fr50 out of range. mem_addr<=0xFFFF.");
      return;
    }

    uint16_t memAddr = (uint16_t)memAddrUL;
    uint8_t value = 0;

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!framRawReadByte(FRAM_SIMPLE_ADDR, memAddr, value)) {
      Serial.printf("FRAM 0x%02X read failed at mem 0x%04X\n", FRAM_SIMPLE_ADDR, memAddr);
      return;
    }

    Serial.printf("FRAM 0x%02X read OK: mem 0x%04X => 0x%02X (%u)\n",
                  FRAM_SIMPLE_ADDR, memAddr, value, value);
    return;
  }

  //-----temporary I2C scanner on configured bus: i2cscan;
  if (strcmp(cmd, "i2cscan") == 0) {
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    Serial.printf("I2C scan start (SDA=%d, SCL=%d, %d Hz)\n",
                  I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);

    uint8_t found = 0;
    for (uint8_t addr = 1; addr < 0x80; ++addr) {
      Wire.beginTransmission(addr);
      uint8_t err = Wire.endTransmission();
      if (err == 0) {
        Serial.printf("I2C device found at 0x%02X\n", addr);
        found++;
      } else if (err == 4) {
        Serial.printf("I2C unknown error at 0x%02X\n", addr);
      }
    }

    if (found == 0) {
      Serial.println("I2C scan done: no devices found.");
    } else {
      Serial.printf("I2C scan done: %u device(s) found.\n", found);
    }
    return;
  }

  //-----raw FRAM write byte: fwrite<dev_addr>,<mem_addr>,<value>;
  // examples: fwrite0x50,0,123;  fwrite0x51,0x0100,0xAB;
  if (strncmp(cmd, "fwrite", 6) == 0) {
    char *p = cmd + 6;
    char *end = nullptr;

    unsigned long devAddrUL = strtoul(p, &end, 0);
    if (end == p || *end != ',') {
      Serial.println("Error: malformed fwrite. Use fwrite<dev_addr>,<mem_addr>,<value>;");
      return;
    }

    p = end + 1;
    unsigned long memAddrUL = strtoul(p, &end, 0);
    if (end == p || *end != ',') {
      Serial.println("Error: malformed fwrite. Use fwrite<dev_addr>,<mem_addr>,<value>;");
      return;
    }

    p = end + 1;
    unsigned long valueUL = strtoul(p, &end, 0);
    if (end == p || *end != 0) {
      Serial.println("Error: malformed fwrite. Use fwrite<dev_addr>,<mem_addr>,<value>;");
      return;
    }

    if (devAddrUL > 0x7F || memAddrUL > 0xFFFF || valueUL > 0xFF) {
      Serial.println("Error: fwrite out of range. dev_addr<=0x7F, mem_addr<=0xFFFF, value<=0xFF.");
      return;
    }

    uint8_t devAddr = (uint8_t)devAddrUL;
    uint16_t memAddr = (uint16_t)memAddrUL;
    uint8_t value = (uint8_t)valueUL;

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!framRawWriteByte(devAddr, memAddr, value)) {
      Serial.printf("FRAM raw write failed at dev 0x%02X, mem 0x%04X\n", devAddr, memAddr);
      return;
    }

    Serial.printf("FRAM raw write OK: dev 0x%02X, mem 0x%04X <= 0x%02X\n",
                  devAddr, memAddr, value);
    return;
  }

  //-----raw FRAM read byte: fread<dev_addr>,<mem_addr>;
  // examples: fread0x50,0;  fread0x51,0x0100;
  if (strncmp(cmd, "fread", 5) == 0) {
    char *p = cmd + 5;
    char *end = nullptr;

    unsigned long devAddrUL = strtoul(p, &end, 0);
    if (end == p || *end != ',') {
      Serial.println("Error: malformed fread. Use fread<dev_addr>,<mem_addr>;");
      return;
    }

    p = end + 1;
    unsigned long memAddrUL = strtoul(p, &end, 0);
    if (end == p || *end != 0) {
      Serial.println("Error: malformed fread. Use fread<dev_addr>,<mem_addr>;");
      return;
    }

    if (devAddrUL > 0x7F || memAddrUL > 0xFFFF) {
      Serial.println("Error: fread out of range. dev_addr<=0x7F, mem_addr<=0xFFFF.");
      return;
    }

    uint8_t devAddr = (uint8_t)devAddrUL;
    uint16_t memAddr = (uint16_t)memAddrUL;
    uint8_t value = 0;

    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
    if (!framRawReadByte(devAddr, memAddr, value)) {
      Serial.printf("FRAM raw read failed at dev 0x%02X, mem 0x%04X\n", devAddr, memAddr);
      return;
    }

    Serial.printf("FRAM raw read OK: dev 0x%02X, mem 0x%04X => 0x%02X (%u)\n",
                  devAddr, memAddr, value, value);
    return;
  }

  //-------zero------
  if (cmd[0] == 'z' && cmd[1] == 0) {
  pcntZero(pcX);
  pcntZero(pcY);
  pcntZero(pcZ);
  y_offset = 0;

  sendAck('z');
  sendCoordsPacket(0x22);
  return;
}

  // read power supply PS0 (send: ps0;)
  if (cmd[0] == 'p' && cmd[1] == 's' && cmd[2] == '0' && cmd[3] == 0) {
    readPS();
    Serial.print("PS0 voltage: ");
    Serial.print(PSV, 4);
    Serial.println(" V");
    return;
  }

  //-----coords packet
  if (cmd[0] == 'p' && cmd[1] == 0) {
    sendAck('p');
    sendCoordsPacket(0x20);
    return;
  }

  //-----print raw pcnt32 values in human-readable text
  if (cmd[0] == 'P' && cmd[1] == 0) {
    printPcnt32ValuesHuman();
    return;
  }

  //-----print current pcnt32 axis limits in human-readable text
  if (cmd[0] == 'L' && cmd[1] == 0) {
    printPcnt32LimitsHuman();
    return;
  }

  //-----print current step timing values in human-readable text
  if (cmd[0] == 'D' && cmd[1] == 0) {
    printStepDelaysHuman();
    return;
  }

  //-----print current integration time in human-readable text
  if (strcmp(cmd, "itime") == 0) {
    printIntegrationTimeHuman();
    return;
  }

  //-----pcnt32 axis limits in binary packet
  if (cmd[0] == 'l' && cmd[1] == 0) {
    sendAck('l');
    sendPcnt32LimitsPacket();
    return;
  }

  //-----step timings in binary packet
  if (cmd[0] == 'd' && cmd[1] == 0) {
    sendAck('d');
    sendStepDelaysPacket();
    return;
  }

  //-----integration time in binary packet
  if (strcmp(cmd, "it") == 0) {
    sendAck('I');
    sendIntegrationTimePacket();
    return;
  }

  //-----set pcnt32 axis limits: lc<xmin>,<xmax>,<ymin>,<ymax>,<zmin>,<zmax>;
  if (trySetPcnt32LimitsFromCommand(cmd)) {
    return;
  }

  //-----set step timings: stepdelays<pulse_us>,<gap_us>;
  if (trySetStepDelaysFromCommand(cmd)) {
    return;
  }

  //-----print device model and firmware version in human-readable text
  if (strcmp(cmd, "info") == 0) {
    printDeviceInfoHuman();
    return;
  }

  //-----set integration time: i700;
  if (cmd[0] == 'i') {
    char *end = nullptr;
    uint32_t v = (uint32_t)strtoul(cmd + 1, &end, 10);
    if (end == cmd + 1 || *end != 0) {
      sendErr('i', 0x01);
      return;
    }

    if (v < 50) v = 50;          // simple guard
    if (v > 50000) v = 50000;    // simple guard
    integraltimemicros = v;
    sendAck('i');
    return;
  }

  //-----select capacitor: cint (CAP_SEL_0 LOW), cext (CAP_SEL_0 HIGH)
  if (strcmp(cmd, "cint") == 0) {
    selectCapacitor(false);
    sendAck('c');
    printCapacitorSelectionHuman();
    return;
  }

  if (strcmp(cmd, "cext") == 0) {
    selectCapacitor(true);
    sendAck('c');
    printCapacitorSelectionHuman();
    return;
  }

  //-----read capacitor selection state: cstate
  if (strcmp(cmd, "cstate") == 0) {
    printCapacitorSelectionHuman();
    return;
  }

  //-----toggle error mode: eh0 (binary), eh1 (human-readable)
  if (cmd[0] == 'e' && cmd[1] == 'h' && (cmd[2] == '0' || cmd[2] == '1') && cmd[3] == 0) {
    error_messages_human = (cmd[2] == '1');
    if (error_messages_human) {
      Serial.println("Error output mode: human-readable");
    } else {
      sendAck('h');
    }
    return;
  }

  //-----set dark current automatically to <= 0 V on ch0 and ch1: sdc[step];
  // examples: sdc; (default step 10), sdc10;, sdc20; ... sdc100;
  if (strncmp(cmd, "sdc", 3) == 0 && cmd[3] != 'v') {
    uint16_t codeStep = 10;
    if (cmd[3] != 0) {
      char *end = nullptr;
      long stepLong = strtol(cmd + 3, &end, 10);
      if (end == cmd + 3 || *end != 0) {
        sendErr('s', 0x01);
        Serial.println("Error: malformed sdc command. Use sdc; or sdc<1-100>;");
        return;
      }

      if (stepLong < 1 || stepLong > 100) {
        sendErr('s', 0x02);
        Serial.println("Error: sdc step out of range. Use integer step 1..100.");
        return;
      }

      codeStep = (uint16_t)stepLong;
    }

    if (!setDarkCurrentToZeroVolts(codeStep)) {
      if (sdc_cancel_requested) {
        sendErr('s', 0x08);
      } else {
      sendErr('s', 0x03);
      }
      return;
    }

    sendAck('s');
    return;
  }

  //-----set dark current automatically to <= target volts on ch0 and ch1: sdcv[target][,step];
  // examples:
  //   sdcv;            (default target -10.0 V, default step 10)
  //   sdcv-10.2;       (target -10.2 V, default step 10)
  //   sdcv-10.2,25;    (target -10.2 V, step 25)
  //   sdcv,25;         (default target -10.0 V, step 25)
  if (strncmp(cmd, "sdcv", 4) == 0) {
    float targetVolts = -10.0f;
    uint16_t codeStep = 10;
    char *p = cmd + 4;

    if (*p != 0) {
      char *end = nullptr;

      // Optional explicit default-target marker: sdcv,<step>;
      if (*p == ',') {
        p++;
      } else {
        targetVolts = strtof(p, &end);
        if (end == p) {
          sendErr('s', 0x04);
          Serial.println("Error: malformed sdcv command. Use sdcv; sdcv<-10.5..0.0>; or sdcv<-10.5..0.0>,<1-100>;");
          return;
        }
        p = end;
      }

      // Optional code step part: ,<1..100>
      if (*p == ',') {
        long stepLong = strtol(p + 1, &end, 10);
        if (end == (p + 1) || *end != 0) {
          sendErr('s', 0x04);
          Serial.println("Error: malformed sdcv command. Step must be integer 1..100.");
          return;
        }

        if (stepLong < 1 || stepLong > 100) {
          sendErr('s', 0x07);
          Serial.println("Error: sdcv step out of range. Use integer step 1..100.");
          return;
        }

        codeStep = (uint16_t)stepLong;
      } else if (*p != 0) {
        sendErr('s', 0x04);
        Serial.println("Error: malformed sdcv command. Use comma before step: sdcv-10.0,10;");
        return;
      }
    }

    // Conversion follows test-sketch scaling, with inverted sign:
    // V = -((code - 32768) * ((5 * Vref) / 65536)), with Vref=4.096V.
    // Valid negative detector target range requested by protocol.
    if (targetVolts < -10.5f || targetVolts > 0.0f) {
      sendErr('s', 0x05);
      Serial.println("Error: sdcv target out of range. Use target voltage from -10.5 V to 0.0 V.");
      return;
    }

    if (!setDarkCurrentToTargetVoltage(targetVolts, codeStep)) {
      if (sdc_cancel_requested) {
        sendErr('s', 0x08);
      } else {
        sendErr('s', 0x06);
      }
      return;
    }

    sendAck('s');
    return;
  }

  //-----stop active dark-current auto-routine: sdcstop;
  if (strcmp(cmd, "sdcstop") == 0) {
    if (sdc_routine_active) {
      sdc_cancel_requested = true;
      Serial.println("sdcstop accepted. Current sdc/sdcv routine will stop.");
    } else {
      Serial.println("sdcstop received, but no sdc/sdcv routine is active.");
    }
    return;
  }

  //-----set dark-current DAC code: dc<channel>,<code>; e.g. dc0,3000;
  if (cmd[0] == 'd' && cmd[1] == 'c') {
    char *p = cmd + 2;
    char *end = nullptr;

    long ch = strtol(p, &end, 10);
    if (end == p || *end != ',') {
      sendErr('c', 0x01);
      Serial.println("Error: malformed dc command. Use dc<0|1>,<0-65535>;");
      return;
    }

    p = end + 1;
    long code = strtol(p, &end, 10);
    if (end == p || *end != 0) {
      sendErr('c', 0x01);
      Serial.println("Error: malformed dc command. Use dc<0|1>,<0-65535>;");
      return;
    }

    if ((ch != 0 && ch != 1) || code < 0 || code > 65535) {
      sendErr('c', 0x02);
      Serial.println("Error: dc values out of range. Channel must be 0/1 and code 0..65535.");
      return;
    }

    if (!ad5675_write_update((uint8_t)ch, (uint16_t)code)) {
      sendErr('c', 0x03);
      Serial.println("Error: AD5675 I2C write failed.");
      return;
    }

    sendAck('c');
    Serial.print("Dark current DAC set: ch");
    Serial.print((int)ch);
    Serial.print(" = ");
    Serial.println((int)code);
    return;
  }

  //-----set manual potentiometer value: q0; ... q1023;
  if (cmd[0] == 'q') {
    Serial.print("Received command: ");
    Serial.println(cmd);

    char *end = nullptr;
    long v = strtol(cmd + 1, &end, 10);
    if (end == cmd + 1 || *end != 0) {
      sendErr('q', 0x01);
      Serial.println("Error: malformed q command. Use q<0-1023>;");
      return;
    }

    if (v < 0 || v > 1023) {
      sendErr('q', 0x02);
      Serial.print("Error: q value out of range (0-1023): ");
      Serial.println(v);
      return;
    }

    pot_value = (uint16_t)v;
    setPot(pot_value);
    sendAck('q');
    Serial.print("Potentiometer set to: ");
    Serial.println(pot_value);
    return;
  }

  //-----regulate PS0 automatically: r<voltage>; e.g. r42.32;
  if (cmd[0] == 'r' && cmd[1] >= '0' && cmd[1] <= '9') {
    char *end = nullptr;
    float targetV = strtof(cmd + 1, &end);
    if (end == cmd + 1 || *end != 0) {
      sendErr('r', 0x01);
      Serial.println("Error: malformed r command. Use r<target_voltage>; e.g. r42.32;");
      return;
    }

    regulatePS(targetV);
    return;
  }

  //-----average detector channel and print human-readable result:
  // avgdet<channel>[,<samples>]; examples: avgdet0; avgdet1,250;
  if (strncmp(cmd, "avgdet", 6) == 0) {
    char *p = cmd + 6;
    char *end = nullptr;

    long ch = strtol(p, &end, 10);
    if (end == p) {
      Serial.println("Error: malformed avgdet command. Use avgdet<0|1>[,<samples>];");
      return;
    }

    uint32_t samples = 100;
    if (*end == ',') {
      p = end + 1;
      samples = (uint32_t)strtoul(p, &end, 10);
      if (end == p || *end != 0) {
        Serial.println("Error: malformed avgdet command. Use avgdet<0|1>[,<samples>];");
        return;
      }
    } else if (*end != 0) {
      Serial.println("Error: malformed avgdet command. Use avgdet<0|1>[,<samples>];");
      return;
    }

    detReadAverageAndPrintHuman((uint8_t)ch, samples, nullptr, true);
    return;
  }

  //-----read detector values and send bytes: readbytesN; e.g. readbytes100;
  if (strncmp(cmd, "readbytes", 9) == 0) {
    char *end = nullptr;
    uint32_t N = (uint32_t)strtoul(cmd + 9, &end, 10);
    if (end == cmd + 9 || *end != 0) {
      sendErr('r', 0x02);
      return;
    }

    detReadAndSendBytes(N);
    return;
  }

  //-----manual control for GPIO21 timing pin: pin21H; / pin21L;
  if (strcmp(cmd, "pin21H") == 0) {
    digitalWrite(SERIAL_TIMING_PIN, HIGH);
    Serial.println("GPIO21 set HIGH");
    return;
  }

  if (strcmp(cmd, "pin21L") == 0) {
    digitalWrite(SERIAL_TIMING_PIN, LOW);
    Serial.println("GPIO21 set LOW");
    return;
  }

    //-----continuous human detector stream: start; ... stop;
  if (strcmp(cmd, "start") == 0) {
    detReadAndPrintHumanStart();
    return;
  }

  if (strcmp(cmd, "stop") == 0) {
    detReadAndPrintHumanStop();
    return;
  }

  //-----continuous detector stream in bytes: rs; ... re;
  //-----pulse-count detector mode with optional threshold and dose factors:
  //     rsp[<threshold>[,<ACR>[,<CF>]]]; ... re;
  //     defaults: threshold=-9.0, ACR=1.0, CF=1.0
  //     examples: rsp; / rsp-9.2; / rsp-9.2,1.15,0.73; / rsp,1.15,0.73;
  if (strncmp(cmd, "rsp", 3) == 0) {
    float thresholdV = -9.0f;
    float acr = 1.0f;
    float cf = 1.0f;
    char *p = cmd + 3;

    if (*p == 0) {
      detReadAndCountPulsesStart(thresholdV, acr, cf);
      return;
    }

    if (*p == ',') {
      char *endAcr = nullptr;
      acr = strtof(p + 1, &endAcr);
      if (endAcr == p + 1) {
        Serial.println("Error: malformed rsp command. Invalid ACR value.");
        return;
      }

      if (*endAcr == ',') {
        char *endCf = nullptr;
        cf = strtof(endAcr + 1, &endCf);
        if (endCf == endAcr + 1 || *endCf != 0) {
          Serial.println("Error: malformed rsp command. Invalid CF value.");
          return;
        }
      } else if (*endAcr != 0) {
        Serial.println("Error: malformed rsp command. Use rsp[<threshold>[,<ACR>[,<CF>]]];");
        return;
      }
    } else {
      char *endThreshold = nullptr;
      thresholdV = strtof(p, &endThreshold);
      if (endThreshold == p) {
        Serial.println("Error: malformed rsp command. Invalid threshold value.");
        return;
      }

      if (*endThreshold == ',') {
        char *endAcr = nullptr;
        acr = strtof(endThreshold + 1, &endAcr);
        if (endAcr == endThreshold + 1) {
          Serial.println("Error: malformed rsp command. Invalid ACR value.");
          return;
        }

        if (*endAcr == ',') {
          char *endCf = nullptr;
          cf = strtof(endAcr + 1, &endCf);
          if (endCf == endAcr + 1 || *endCf != 0) {
            Serial.println("Error: malformed rsp command. Invalid CF value.");
            return;
          }
        } else if (*endAcr != 0) {
          Serial.println("Error: malformed rsp command. Use rsp[<threshold>[,<ACR>[,<CF>]]];");
          return;
        }
      } else if (*endThreshold != 0) {
        Serial.println("Error: malformed rsp command. Use rsp[<threshold>[,<ACR>[,<CF>]]];");
        return;
      }
    }

    detReadAndCountPulsesStart(thresholdV, acr, cf);
    return;
  }

  if (strcmp(cmd, "rs") == 0) {
    detReadAndSendBytesStart();
    return;
  }

  if (strcmp(cmd, "re") == 0) {
    if (det_pulse_count_streaming) {
      detReadAndCountPulsesStopAndPrint();
    } else {
      detReadAndSendBytesStop();
    }
    return;
  }

  //-----continuous detector+temperature stream in bytes: rts; ... rte;
  if (strcmp(cmd, "rts") == 0) {
    detReadAndSendBytesWithTempStart();
    return;
  }

  if (strcmp(cmd, "rte") == 0) {
    detReadAndSendBytesWithTempStop();
    return;
  }

  //-----read and print detector values: readN; e.g. read100;
  if (strncmp(cmd, "read", 4) == 0) {
    char *end = nullptr;
    uint32_t N = (uint32_t)strtoul(cmd + 4, &end, 10);
    if (end == cmd + 4 || *end != 0) {
      Serial.println("Error: malformed read command. Use readN; e.g. read100;");
      return;
    }

    detReadAndPrintHuman(N);
    return;
  }

  //============================================================
  // XYZ sequential move in steps: "M<x>,<y>,<z>"
  // Moves one motor at a time in this order: X -> Y -> Z
  //============================================================
  if (cmd[0] == 'M') {
    char *p = cmd + 1;
    char *end = nullptr;

    long xStepsL = strtol(p, &end, 10);
    if (end == p || *end != ',') {
      sendErr('M', 0x01);
      Serial.println("Error: malformed M command. Use M<x_steps>,<y_steps>,<z_steps>;");
      return;
    }

    p = end + 1;
    long yStepsL = strtol(p, &end, 10);
    if (end == p || *end != ',') {
      sendErr('M', 0x01);
      Serial.println("Error: malformed M command. Use M<x_steps>,<y_steps>,<z_steps>;");
      return;
    }

    p = end + 1;
    long zStepsL = strtol(p, &end, 10);
    if (end == p || *end != 0) {
      sendErr('M', 0x01);
      Serial.println("Error: malformed M command. Use M<x_steps>,<y_steps>,<z_steps>;");
      return;
    }

    int32_t xSteps = (int32_t)xStepsL;
    int32_t ySteps = (int32_t)yStepsL;
    int32_t zSteps = (int32_t)zStepsL;

    if (!moveXYZSequentialStepsWithLimitCheck(xSteps, ySteps, zSteps)) {
      return;
    }

    return;
  }

  //============================================================
  // Unlimited independent/coupled move (no limit checks):
  // "ux200" "uy-50" "uz1000" "uZ300"
  //============================================================
  if (cmd[0] == 'u') {
    char axis = cmd[1];
    if (!(axis == 'x' || axis == 'y' || axis == 'z' || axis == 'Z')) {
      sendErr('u', 0x01);
      return;
    }

    char *end = nullptr;
    long nLong = strtol(cmd + 2, &end, 10);
    if (end == cmd + 2 || *end != 0) {
      sendErr('u', 0x01);
      return;
    }

    int32_t n = (int32_t)nLong;
    sendAck('u');

    if (axis == 'Z') {
      int32_t y_before = pcntRead32(pcY);
      moveYZCoupledSteps(n);
      int32_t y_after = pcntRead32(pcY);
      y_offset -= (y_after - y_before);
    } else {
      moveAxisSteps(axis, n);
    }

    sendCoordsPacket(0x21);
    return;
  }

  //============================================================
  // Coupled move: "Z200" or "Z-50"
  // TRUE step-by-step coupling Y+Z
  //============================================================
  if (cmd[0] == 'Z') {
  int32_t n = (int32_t)strtol(cmd + 1, nullptr, 10);
  if (!checkCoupledYZMoveLimit(n)) {
    return;
  }

  sendAck('Z');

  int32_t y_before = pcntRead32(pcY);
  moveYZCoupledSteps(n);
  int32_t y_after = pcntRead32(pcY);
  y_offset -= (y_after - y_before);

  sendCoordsPacket(0x21);
  return;
  }

  //============================================================
  // Independent axis move: "x200" "y-50" "z1000"
  //============================================================
  char a = (char)tolower(cmd[0]);
  if (a == 'x' || a == 'y' || a == 'z') {
    int32_t n = (int32_t)strtol(cmd + 1, nullptr, 10);
    if (!checkSingleAxisMoveLimit(a, n)) {
      return;
    }

    sendAck((uint8_t)a);

    moveAxisSteps(a, n);

    sendCoordsPacket(0x21);
    return;
  }

}
