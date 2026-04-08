#include "Arduino.h"
#include <Adafruit_MCP9808.h>
#include <Adafruit_FRAM_I2C.h>
//#include "ADS8688.h"
#include "driver/adc.h" 
#include "esp_timer.h"
#include "../lib/ADC/SPIADC2.h"  //#include "../lib/ADC/SPIADC.h"

#define CS_POT      36

#define RST_PIN     40 
#define HOLD_PIN    41

#define CS_PIN      37
#define SCK_PIN     12
#define MISO_PIN    13
#define MOSI_PIN    11

#define SDA_PIN     8
#define SCL_PIN     9

// #define SIGLED_PIN  25

#define CAP_SEL_PIN_0 2
#define CAP_SEL_PIN_1 42

// #define INPUT_PIN    34
static const adc1_channel_t CHANNEL = ADC1_CHANNEL_6;   // GPIO34 come esempio


#define HOLD_PERIOD          10      //us
#define RST_PERIOD           30//10      //us
#define INTEGRATE_PERIOD     700     //500//100    //us
#define TOTAL_PERIOD         INTEGRATE_PERIOD+RST_PERIOD+HOLD_PERIOD//500     //700//(HOLD_PERIOD + RST_PERIOD + INTEGRATE_PERIOD)

#define PROMEDIO 3

#define SPI_CLOCK_MHZ 1


uint16_t val0 = 0;
uint16_t val1 = 0;
float    val0Volt = 0.0f;
float    val1Volt = 0.0f;

#define READ_AND_PRINT
#define SPI_ADC


esp_timer_handle_t adc_timer;
//esp_timer_handle_t adc_timer2;

volatile bool start_reading = false;
volatile bool stop_reading = false;

Adafruit_MCP9808 tempsensor = Adafruit_MCP9808();
Adafruit_FRAM_I2C fram = Adafruit_FRAM_I2C();
SpiAdc spiAdc(CS_PIN, SCK_PIN, MISO_PIN, MOSI_PIN);  

SPISettings spiSettings(SPI_CLOCK_MHZ * 1000000, MSBFIRST, SPI_MODE0);

static const uint8_t AD5675_ADDR = 0x0F;
static const uint8_t CMD_WRITE_UPDATE = 0x03;
static const uint8_t CMD_POWER_UP = 0x08;

#define CYCLES_TO_PRINT   5000

void adc_timer_callback(void* arg) {
    start_reading = true;
}

// void adc_timer_callback2(void* arg) {
//     stop_reading = true;
// }

void hold(bool sample){
    digitalWrite(RST_PIN, HIGH);
    digitalWrite(HOLD_PIN, HIGH);


    if(sample){

        #ifdef SPI_ADC
        uint32_t sum0 = 0;
        uint32_t sum1 = 0;

        #ifdef PROMEDIO
        for(uint8_t i=0; i<PROMEDIO; i++){
            sum0 += spiAdc.readRaw0();//spiAdc.readRaw0();
            sum1 += spiAdc.readRaw1();//spiAdc.readRaw0();
        }
        val0 = (uint16_t)(sum0/PROMEDIO);
        val1 = (uint16_t)(sum1/PROMEDIO);
        //val0 = spiAdc.readRaw1(PROMEDIO); //(uint16_t)(sum/PROMEDIO);

        #else
        val0     = spiAdc.readRaw0(); 
        #endif

        val0Volt = spiAdc.codeToVolt(val0);
        val1Volt = spiAdc.codeToVolt(val1);

        #else
        val0 =  adc1_get_raw(CHANNEL); // analogReadMilliVolts(INPUT_PIN);//adc.I2V(adc.noOp(),adc.getChannelRange(0));
        //val1 = adc.I2V(adc.noOp(),adc.getChannelRange(1));    
        #endif
        
    }
    

}

void reset(){
    digitalWrite(RST_PIN, LOW);
    digitalWrite(HOLD_PIN, HIGH);

    //digitalWrite(CS_PIN, HIGH);
    //digitalWrite(SCK_PIN, HIGH);
}

#define OUTPUT_PULSE false

void integrate(){


    digitalWrite(RST_PIN, HIGH);
    digitalWrite(HOLD_PIN, LOW);


    #if OUTPUT_PULSE
        static bool pusle = false;
        pusle = !pusle;

        if(pusle){
            
            const uint8_t pulse_period = 10;
            delayMicroseconds(100-6);
            dacWrite(SIGLED_PIN, 150);
            delayMicroseconds(pulse_period-6);
            //pinMode(SIGLED_PIN, OUTPUT);
            //digitalWrite(SIGLED_PIN, false);
            dacWrite(SIGLED_PIN, 0);
            delayMicroseconds(INTEGRATE_PERIOD-100-pulse_period);
        }
        else delayMicroseconds(INTEGRATE_PERIOD);
        
    #else
        delayMicroseconds(INTEGRATE_PERIOD);
    #endif
    // esp_timer_start_once(adc_timer2, INTEGRATE_PERIOD);
    // Serial.printf("%.4fV\n", val0Volt);
    // while(!stop_reading);
    // stop_reading = false;
    // esp_timer_stop(adc_timer2);
}

// --------------------- POTENCIÓMETRO ---------------------
// === Comandos (byte de comando según datasheet) ===
static constexpr uint8_t CMD_WRITE_WIPER1 = 0x01; // Write Wiper Register 1 (H1-W1-L1)
static constexpr uint8_t CMD_WRITE_NV1    = 0x11; // Write NV Register 1 (no mueve wiper)
static constexpr uint8_t CMD_COPY_W1_TO_NV1 = 0x21; // 8-bit: Copy Wiper1 -> NV1
static constexpr uint8_t CMD_COPY_NV1_TO_W1 = 0x31; // 8-bit: Copy NV1 -> Wiper1

/**
 * @brief Cambia la posición del wiper W1 del MAX
 * @param reg Indica el registro sobre el que se quiere escribir
 * (Wiper Register 1 = 0x01)
 * @param position Indica la posición a la que se quiere poner el wiper.
 * El rango es de 0 a 1023
* Envía un frame de 24 bits: [cmd<<16][data(10b)<<6][don't care(6b)]
*/
static void max5494_set_wiper_position(uint8_t cmd, uint16_t position){
    position &= 0x03FF; // 10 bits

  // Estructura práctica: cmd en el byte alto (1-8), datos alineados a la izquierda en los 16 bits siguientes
  uint32_t frame = (cmd << 16) | (position << 6);

  SPI.beginTransaction(spiSettings);
  digitalWrite(CS_POT, LOW);

  SPI.transfer((frame >> 16) & 0xFF);
  SPI.transfer((frame >>  8) & 0xFF);
  SPI.transfer((frame >>  0) & 0xFF);

  digitalWrite(CS_POT, HIGH);
  SPI.endTransaction();
}

static void max5494_cmd(uint8_t cmd){
  SPI.beginTransaction(spiSettings);
  digitalWrite(CS_POT, LOW);
  SPI.transfer(cmd);
  digitalWrite(CS_POT, HIGH);
  SPI.endTransaction();
  delay(12);
}

uint8_t ad5675_write_update(uint8_t ch, uint16_t code){
  Wire.beginTransmission(0x0F);//(AD5675_ADDR);
  uint8_t commandByte = (CMD_WRITE_UPDATE << 4) | (ch);//& 0x0F);
  Wire.write(0x30 | ch);//(commandByte);
  Wire.write((uint8_t)(code >> 8));
  Wire.write((uint8_t)(code & 0xFF));
  Wire.endTransmission();
  return (1);
}

void setup(){
    const esp_timer_create_args_t timer_args = {
        .callback = &adc_timer_callback,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "adc_us_timer"
    };

    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, CS_POT);

    uint16_t wiperPosition = 10;
    max5494_set_wiper_position(CMD_WRITE_WIPER1, wiperPosition);  // Movemos el wiper a la posición indicada
    max5494_cmd(CMD_COPY_W1_TO_NV1); // Guardamos la posición del wiper a NV1 (Non-Volatile Register 1)

    // const esp_timer_create_args_t timer_args2 = {
    //     .callback = &adc_timer_callback2,
    //     .arg = nullptr,
    //     .dispatch_method = ESP_TIMER_TASK,
    //     .name = "adc_us_timer2"
    // };

    esp_timer_create(&timer_args, &adc_timer);
    //esp_timer_create(&timer_args2, &adc_timer2);

    delay(1000);

    pinMode(RST_PIN, OUTPUT);
    pinMode(HOLD_PIN, OUTPUT);
    // pinMode(CAP_SEL_PIN, OUTPUT);
    // digitalWrite(CAP_SEL_PIN, HIGH); 
    pinMode(CAP_SEL_PIN_0, OUTPUT);
    digitalWrite(CAP_SEL_PIN_0, HIGH);


    Wire.begin(SDA_PIN, SCL_PIN, 100000);

    ad5675_write_update(0x00, 30000);
    ad5675_write_update(0x01, 30000);
    tempsensor.begin(0x18, &Wire); //this line on
    tempsensor.setResolution(3); //this line on
    // Mode Resolution SampleTime
    //  0    0.5°C       30 ms
    //  1    0.25°C      65 ms
    //  2    0.125°C     130 ms
    //  3    0.0625°C    250 ms
    tempsensor.wake(); //this line on

    bool x = fram.begin(MB85RC_DEFAULT_ADDRESS, &Wire);


    #ifdef SPI_ADC
    spiAdc.begin();
    #else
    adc1_config_width(ADC_WIDTH_BIT_12);
    // Imposta attenuazione (11 dB = misura fino a ~3.1V)
    adc1_config_channel_atten(CHANNEL, ADC_ATTEN_DB_11);    
    #endif

    reset();
    Serial.begin(115200);
    delay(5000);
    Serial.println("test started");
    Serial1.println("test started");
    Serial2.println("test started");
    //    if(fram.begin(MB85RC_DEFAULT_ADDRESS, &I2Cone))  Serial.printf("FRAM OK");
    // else Serial.printf("FRAM not OK");
    uint16_t manufacturerID = 0, productID = 0;
    fram.getDeviceID(&manufacturerID, &productID);
    Serial.printf("FRAM Manufacturer ID: 0x%04X, 0x%04X, %d\n", manufacturerID, productID, x);

    esp_timer_start_periodic(adc_timer, TOTAL_PERIOD);

}

uint32_t cycles = 0;
float data0[CYCLES_TO_PRINT];
float data1[CYCLES_TO_PRINT];


#define TESTPULSE_LED2 false

void loop(){
    if(!start_reading) return;

    
    
    start_reading = false;
    integrate();
    //delayMicroseconds();
    hold(true);
    #if TESTPULSE_LED2
        dacWrite(SIGLED_PIN, 150);
        delayMicroseconds(4);
        dacWrite(SIGLED_PIN, 0);
    #else
        delayMicroseconds(RST_PERIOD);
    #endif
    reset();
    #if TESTPULSE_LED3
        dacWrite(SIGLED_PIN, 150);
        delayMicroseconds(4);
        dacWrite(SIGLED_PIN, 0);
    #else
        delayMicroseconds(RST_PERIOD);
    #endif
    hold(false);

    data0[cycles] = val0Volt; //val0;
    data1[cycles] = val1Volt; //val1;
    if(cycles>=CYCLES_TO_PRINT){
        //static uint8_t printed = 0;
        //fram.write(0, &printed, sizeof(printed));
        esp_timer_stop(adc_timer);
        uint8_t readData = 0;
        cycles = 0;
        Serial.printf("fram state %d\n", fram.read(0, (uint8_t*)&readData, sizeof(readData))); 
        Serial.printf("fram data %d\n", readData);
        Serial.printf("temp: %.2fºC\n", tempsensor.readTempC()); 
        Serial.println("-- start printing data ch0--");
        const uint8_t offset = 5;
        for(uint16_t i=offset; i<CYCLES_TO_PRINT-offset; i++){
            Serial.printf("%.3f;", data0[i]);
        }
        Serial.println("-- start printing data ch1--");
        for(uint16_t i=offset; i<CYCLES_TO_PRINT-offset; i++){
            Serial.printf("%.3f;", data1[i]);
        }
        Serial.println("-- finish printing data --");
        readData++;
        fram.write(0, &readData, sizeof(readData));
        esp_timer_start_periodic(adc_timer, TOTAL_PERIOD);
        //printed ++;
    }
    cycles++;

    //Serial.printf("%.4fV\n", val0Volt);
    
}
