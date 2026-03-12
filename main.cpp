/**
  ******************************************************************************
  * @file           : main.cpp
  * @brief          : Test frimware for [PXXXYYYR] from [project name] main PCB
  ******************************************************************************
  *
  * Version Control
  *
  * version:        : 0.0.0
  *
  ******************************************************************************
  * @attention
  *
  *
  ******************************************************************************
*/

/*    Includes ---------------------------------------------------------------*/
#include "Wire.h"
#include <esp_task_wdt.h>
#include <SPI.h>
#include <math.h>

#include "soc/rtc_io_reg.h"
#include "soc/sens_reg.h"

#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <Adafruit_ADS1X15.h>
#include <Defines.h>
#include <USB.h>
#include <Steppers.h>

/*    Defines ---------------------------------------------------------------*/

#define TASK_LOOP_PERIODICITY   200  // ms

// === Comandos (byte de comando según datasheet) ===
static constexpr uint8_t CMD_WRITE_WIPER1 = 0x01; // Write Wiper Register 1 (H1-W1-L1)
static constexpr uint8_t CMD_WRITE_NV1    = 0x11; // Write NV Register 1 (no mueve wiper)
static constexpr uint8_t CMD_COPY_W1_TO_NV1 = 0x21; // 8-bit: Copy Wiper1 -> NV1
static constexpr uint8_t CMD_COPY_NV1_TO_W1 = 0x31; // 8-bit: Copy NV1 -> Wiper1

/*    Typedef ------------------------------------------------------------*/

/*    Variables ----------------------------------------------------------*/

Adafruit_ADS1115 ads1115;

static const uint8_t AD5675_ADDR = 0x0F;
static const uint8_t CMD_WRITE_UPDATE = 0x3;

/*    Function Prototypes ----------------------------------------------------------*/


/*    Function Definitions ----------------------------------------------------------*/


// --------------------- HAL I2C ---------------------

void i2c_scan(){
  Serial.println("\nScanning I2C...");
  byte error, address; //variable for error and I2C address
  int nDevices;

  nDevices = 0;
  for (address = 1; address < 127; address++ ){
    // The I2C scanner uses the return value of
    // the Write.endTransmission to see if
    // a device acknowledged to the address.
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0){
      Serial.print("\nI2C device found at address 0x");
      if (address < 16)
        Serial.print("0");
      Serial.print(address, HEX);
      Serial.println("  !");
      nDevices++;
    }
    else if (error == 4){
      Serial.print("\nUnknown error at address 0x");
      if (address < 16)
        Serial.print("0");
      Serial.println(address, HEX);
    }
  }
  if (nDevices == 0)
    Serial.println("\nNo I2C devices found\n");
  else
    Serial.println("\nI2C scan done ----------\n");
}


// --------------------- POTENCIÓMETRO ---------------------

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


// --------------------- DAC ---------------------

/**
 * @brief Escribe y actualiza un registro del DAC
 * @param ch Registro sobre el que se quiere escribir (para validación sólo 0 o 1)
 * @param code Valor a escribir (16 bits)
 */
uint8_t ad5675_write_update(uint8_t ch, uint16_t code){
  Wire.beginTransmission(AD5675_ADDR);
  uint8_t commandByte = (CMD_WRITE_UPDATE << 4) | (ch & 0x0F);
  Wire.write(commandByte);
  Wire.write((uint8_t)(code >> 8));
  Wire.write((uint8_t)(code & 0xFF));
  return (Wire.endTransmission());
}

/*    SETUP ---------------------------------------------------------------*/
/*-------------------------------------------------------------------------*/
void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  delay(1000);
  

  Serial.println("\nSystem Initializations .....................................");

  // I2C and ADC init
  Wire.begin(I2C_SDA, I2C_SCL);
  if (!ads1115.begin(0x48)){
    Serial.println("ADS1115 not found!");
  }
  ads1115.setGain(GAIN_ONE);

    //LED setup
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);

    // Setup pins
  pinMode(FAN_EN, OUTPUT);
  pinMode(SYNC_SIGNAL, OUTPUT);

    // Setup steppers
  pinMode(MX_ENC_A, INPUT);
  pinMode(MX_ENC_B, INPUT);
  pinMode(MY_ENC_A, INPUT);
  pinMode(MY_ENC_B, INPUT);
  pinMode(MZ_ENC_A, INPUT);
  pinMode(MZ_ENC_B, INPUT);

    // Setup SPI
  pinMode(CS_POT, OUTPUT);
  pinMode(CS_ADQ, OUTPUT);
  pinMode(CS_USB, OUTPUT);
  pinMode(SPI_SDI, OUTPUT);
  pinMode(SPI_SCLK, OUTPUT);
  pinMode(SPI_SDO, INPUT);

  digitalWrite(CS_POT, HIGH);
  digitalWrite(CS_ADQ, HIGH);
  digitalWrite(CS_USB, HIGH);
  SPI.begin(SPI_SCLK, SPI_SDO, SPI_SDI, CS_POT);

    // Attach interrupts for encoders
  attachInterrupt(digitalPinToInterrupt(MX_ENC_A), isr_stepperX, RISING);
  attachInterrupt(digitalPinToInterrupt(MY_ENC_A), isr_stepperY, RISING);
  attachInterrupt(digitalPinToInterrupt(MZ_ENC_A), isr_stepperZ, RISING);

  set_max_speed(20000);
  
  Serial.println("\nSystem Initialized     .....................................");

}/*    END SETUP ----------------------------------------------------------*/

/*    LOOP ---------------------------------------------------------------*/
/*------------------------------------------------------------------------*/
void loop() {
  static TickType_t lastWakeTime = xTaskGetTickCount();
  static uint16_t count = 0;
  static uint16_t SECcount = 0;
  static uint16_t segs     = 0;
  static uint16_t alter    = 0;
  char msg[100];
  static uint16_t TCP_client_count = 0;




  static uint16_t wiperPosition = 0;
  SECcount++;
  //  if(SECcount >= 10){
  if(SECcount >= 5){
    SECcount = 0;
  

    if(alter)
      alter = 0;
    else
      alter = 1;

    segs++;

    /*  TEST 1 second -----------------*/
    if(segs == 1)
    {
      Serial.println("\nTEST 1:      ..........................................");
      #if TEST_MOTORS
        motor_test();
      #endif

      digitalWrite(FAN_EN, HIGH);
      digitalWrite(RED_LED, HIGH);
      

    /*  TEST 2 seconds -----------------*/
    } else if(segs == 2)
    {
      Serial.println("\nTEST 2:      ..........................................");
      digitalWrite(SYNC_SIGNAL, HIGH);
      digitalWrite(GREEN_LED, HIGH);
      
     
    /*  TEST 3 seconds -----------------*/  
    } else if(segs == 3)
    {
      Serial.println("\nTEST 3:      ..........................................");

      int16_t adc0, adc1, adc2, adc3;
      
      adc0 = ads1115.readADC_SingleEnded(0);
      adc1 = ads1115.readADC_SingleEnded(1);
      adc2 = ads1115.readADC_SingleEnded(2);
      adc3 = ads1115.readADC_SingleEnded(3);

      float volts0 = adc0 * 0.000125;
      float volts1 = adc1 * 0.000125;
      float volts2 = adc2 * 0.000125;
      float volts3 = adc3 * 0.000125;

      Serial.print("AIN0 (V): "); Serial.println(volts0, 4);
      Serial.print("AIN1 (V): "); Serial.println(volts1, 4);
      Serial.print("AIN2 (V): "); Serial.println(volts2, 4);
      Serial.print("AIN3 (V): "); Serial.println(volts3, 4);
      Serial.println(" ");
      Serial.println(" ");


    /*  TEST 4 seconds -----------------*/  
    } else if(segs == 4)
    {
      Serial.println("\nTEST 4:      ..........................................");
      uint8_t r1, r2;
      r1 = ad5675_write_update(0x00, 0xFFFF);
      r2 = ad5675_write_update(0x01, 0x8000);
      Serial.printf("DAC 0 al 100/100. Código de respuesta = %d\n", (int)r1);
      Serial.printf("DAC 1 al 50/100. Código de respuesta = %d\n", (int)r2);

      // xTaskCreatePinnedToCore(motor_test, "STEPPERS", 4096, NULL, 1, NULL, 1);

    /*  TEST 5 seconds -----------------*/  
    } else if(segs == 5)
    {
      Serial.println("\nTEST 5:      ..........................................");
      digitalWrite(RED_LED, LOW);
    
    
    /*  TEST 6 seconds -----------------*/
    } else if(segs == 6)
    {
      Serial.println("\nTEST 6:      ..........................................");
      digitalWrite(FAN_EN, LOW);
      digitalWrite(GREEN_LED, LOW);

      wiperPosition = 0;
      Serial.printf("Wiper set to position = %d\n", wiperPosition);
      max5494_set_wiper_position(CMD_WRITE_WIPER1, wiperPosition);  // Movemos el wiper a la posición indicada
      max5494_cmd(CMD_COPY_W1_TO_NV1);

    /*  TEST 7 seconds -----------------*/  
    } else if(segs == 7)
     {
      Serial.println("\nTEST 7:      ..........................................");
      
    /*  TEST 8 seconds -----------------*/
    } else if(segs == 8)
    {
      Serial.println("\nTEST 8:      ..........................................");
      digitalWrite(SYNC_SIGNAL, LOW);
    

    /*  TEST 9 seconds -----------------*/  
    } else if(segs == 9)
    {
      Serial.println("\nTEST 9:      ..........................................");
     

    /*  TEST 10 seconds -----------------*/  
    } else if(segs == 10)
    {
      Serial.println("\nTEST 10:      ..........................................");
      Serial.println("DAC CH 0 = write 0%");
      Serial.println("DAC CH 1 = write 0%");
      uint8_t r1, r2;
      r1 = ad5675_write_update(0x00, 0x0000);
      r2 = ad5675_write_update(0x01, 0x0000);
      Serial.printf("DAC 0 al 0/100. Código de respuesta = %d\n", (int)r1);
      Serial.printf("DAC 1 al 0/100. Código de respuesta = %d\n", (int)r2);


    /*  TEST 11 seconds -----------------*/  
    } else if(segs == 11)
    {
      Serial.println("\nTEST 11:      ..........................................");


    /*  TEST 12 seconds -----------------*/  
    } else if(segs == 12)
    {
      segs = 0;
      Serial.println("\nTEST 12:      ..........................................");


    }
  }


 



  vTaskDelayUntil(&lastWakeTime, pdMS_TO_TICKS(TASK_LOOP_PERIODICITY));
}/*    END LOOP ----------------------------------------------------------*/

/*    FREERTOS TASKS ------------------------------------------------------*/



/*    END OF FILE ----------------------------------------------------------*/