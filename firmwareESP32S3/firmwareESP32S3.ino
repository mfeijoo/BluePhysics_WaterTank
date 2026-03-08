//test
#include <Arduino.h>
#include "driver/pcnt.h"
#include <math.h>
#include <SPI.h>
#include "Adafruit_MCP9808.h"
#include <ADS1115_WE.h> //we are using the chip ADS1115 and this library to read that chip

//=======================================
//Temperature create objects
//=======================================

Adafruit_MCP9808 tempsensor = Adafruit_MCP9808();
ADS1115_WE adc(0x48);

unsigned int tempbytes;

float PSV;
#define PSFC 16.256
#define PSFCind 0.00864
//#define PSFC 1
//#define PSFCind 0


// =================== STEPPER PINS ===================
static const int X_STEP = 19;
static const int X_DIR  = 20;

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
static const float PCNT32_COUNTS_PER_STEP = 0.0625f;

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

// Timing
static volatile uint32_t integraltimemicros = 700; // default 700 us, can set to 200 us
static const uint32_t resettimemicros = 10;

// ADS8688A in model11 uses SPI mode 1 @ 17 MHz.
// Keep same proven settings while bringing detector code here.
static SPISettings detSPI(17000000, MSBFIRST, SPI_MODE1);

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
  return (double)steps * (double)PCNT32_COUNTS_PER_STEP;
}

static void sendErr(uint8_t cmd_id, uint8_t err_code);
static void sendPcnt32LimitsPacket();

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
static const uint8_t PKT_STREAM_START = 0x32;
static const uint8_t PKT_STREAM_SAMPLE = 0x33;
static const uint8_t PKT_STREAM_STOP = 0x34;

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

static void detReadChannels() {
  SPI.beginTransaction(detSPI);

  // ADS8688A manual channel-select command pattern copied from model11:
  // write command for channel N, then next transfer returns previous result.
  // First read after startup may be stale; measurement loop continuously updates.
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer16(0xC000);      // select CH0
  SPI.transfer16(0);
  digitalWrite(CS_ADQ, HIGH);

  digitalWrite(CS_ADQ, LOW);
  SPI.transfer16(0xC400);      // select CH1
  uint16_t v0 = SPI.transfer16(0); // returns CH0
  digitalWrite(CS_ADQ, HIGH);

  digitalWrite(CS_ADQ, LOW);
  SPI.transfer16(0xC000);      // re-select CH0 for next cycle
  uint16_t v1 = SPI.transfer16(0); // returns CH1
  digitalWrite(CS_ADQ, HIGH);

  SPI.endTransaction();

  det_ch0 = v0;
  det_ch1 = v1;
}

static void setPot(uint16_t value) {
  SPI.beginTransaction(SPISettings(7000000, MSBFIRST, SPI_MODE0));

  digitalWrite(CS_POT, LOW);
  SPI.transfer(0x01);
  SPI.transfer16(value << 6);
  digitalWrite(CS_POT, HIGH);

  SPI.endTransaction();
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
    Serial.print("read ");
    Serial.print(measBuf[j].idx);
    Serial.print(": ch0=");
    Serial.print(measBuf[j].ch0);
    Serial.print(", ch1=");
    Serial.println(measBuf[j].ch1);
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
  det_human_streaming = false;

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

static void detReadAndSendBytesService() {
  if (!det_bytes_streaming) return;

  uint32_t now = micros();
  if ((uint32_t)(now - det_bytes_last_us) < (uint32_t)integraltimemicros) return;

  detReadOnce();
  now = micros();
  det_bytes_last_us = now;

  sendPktHeader(PKT_STREAM_SAMPLE);
  Serial.write((uint8_t*)&det_bytes_idx, 4);
  uint32_t dt = (uint32_t)(now - det_bytes_t0_us);
  Serial.write((uint8_t*)&dt, 4);
  Serial.write((uint8_t*)&det_ch0, 2);
  Serial.write((uint8_t*)&det_ch1, 2);
  det_bytes_idx++;
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
  adc.setCompareChannels(ADS1115_COMP_0_GND);
  adc.startSingleMeasurement();
  while(adc.isBusy()){};
  PSV = adc.getResult_V() * PSFC + PSFCind;
}


//============================================================
// Arduino setup/loop
//============================================================
void setup() {
  Serial.begin(115200);
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
  digitalWrite(RST_PIN, HIGH);
  digitalWrite(HOLD_PIN, LOW);

  // SPI
  SPI.begin(DET_SCK, DET_MISO, DET_MOSI);

  //Use this for ADC ADS8688
  //Set ADC range of all channels to +-2.5 * Vref
  SPI.beginTransaction(SPISettings(17000000, MSBFIRST, SPI_MODE1));
  //ch0
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x05 << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch1
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x06 << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch2
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x07 << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch3
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x08 << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch4
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x09 << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch5
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x0A << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch6
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x0B << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //ch7
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer(0x0C << 1 | 1);
  SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);

  SPI.endTransaction();

  adc.init();
  adc.setConvRate(ADS1115_860_SPS);
  adc.setVoltageRange_mV(ADS1115_RANGE_6144);

  //Temperature sensor setup
  tempsensor.begin(0x18);
  tempsensor.setResolution(3); //this line on
  // Mode Resolution SampleTime
  //  0    0.5°C       30 ms
  //  1    0.25°C      65 ms
  //  2    0.125°C     130 ms
  //  3    0.0625°C    250 ms
  tempsensor.wake(); //this line on
  Serial.println("Temp Sensor ready");

}


void loop() {
  char cmd[96];

  detReadAndPrintHumanService();
  detReadAndSendBytesService();

  if (!readCmd(cmd, sizeof(cmd))) return;
  if (cmd[0] == 0) return;


  //measure temperature manually
  if (cmd[0] == 't' && cmd[1] == 0) {
    sendAck('t');
    //Serial.println("Measuring temperature:");
    //temp = tempsensor.readTempC();
    //Serial.print(temp);
    //Serial.println(" C");
    //delay(500);
    tempbytes = tempsensor.read16(0x05);
    Serial.write(0xAA);
    Serial.write(0x55);
    Serial.write((uint8_t*)&tempbytes, 2);
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

  //-----pcnt32 axis limits in binary packet
  if (cmd[0] == 'l' && cmd[1] == 0) {
    sendAck('l');
    sendPcnt32LimitsPacket();
    return;
  }

  //-----set pcnt32 axis limits: lc<xmin>,<xmax>,<ymin>,<ymax>,<zmin>,<zmax>;
  if (trySetPcnt32LimitsFromCommand(cmd)) {
    return;
  }

  //-----set integration time: i700;
  if (cmd[0] == 'i') {
    uint32_t v = (uint32_t)strtoul(cmd + 1, nullptr, 10);
    if (v < 50) v = 50;          // simple guard
    if (v > 50000) v = 50000;    // simple guard
    integraltimemicros = v;
    sendAck('i');
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

    setPot((uint16_t)v);
    sendAck('q');
    Serial.print("Potentiometer set to: ");
    Serial.println((uint16_t)v);
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
  if (strcmp(cmd, "rs") == 0) {
    detReadAndSendBytesStart();
    return;
  }

  if (strcmp(cmd, "re") == 0) {
    detReadAndSendBytesStop();
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
