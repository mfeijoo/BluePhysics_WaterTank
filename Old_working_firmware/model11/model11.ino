#include <ADS1115_WE.h>
#include <SPI.h>
#include <Wire.h>
#include "Adafruit_MCP9808.h"
#include "Adafruit_FRAM_I2C.h"
#include <Adafruit_DotStar.h>

Adafruit_FRAM_I2C fram = Adafruit_FRAM_I2C();

ADS1115_WE adc(0x48);

Adafruit_MCP9808 tempsensor = Adafruit_MCP9808();

// Board updated to work for watertank software

//definitions model 11
#define CS_ADQ 12
#define RST A2
#define HOLD A3
#define SHD_PS A4
#define SHD_REF 2
#define CS_POT A5
#define PSFC 16.256
#define PSFCind 0.00864
//#define PSFC 1
//#define PSFCind 0
#define TEST_PIN 10
#define DSDATAPIN 7
#define DSCLOCKPIN 5
#define C_RANGE 11
#define FAN_ON 13
#define CS_USB 9


Adafruit_DotStar led(1, DSDATAPIN, DSCLOCKPIN, DOTSTAR_BRG);
//dotstar onboard to turn it off
Adafruit_DotStar led0(1, 8, 6, DOTSTAR_BRG);

uint32_t coloroff = led.Color(0, 0, 0);
uint32_t colorred = led.Color(0, 0, 255);
uint32_t colororange = led.Color(255, 122, 0);
uint32_t colormagenta = led.Color(255, 0, 255);
uint32_t colorcyan = led.Color(0, 255, 255);
uint32_t colorgreen = led.Color(0, 255, 0);
uint32_t colorblue = led.Color(255, 0, 0);


// For AD51115 powers
int16_t adc0 = 0;
int16_t adc1 = 0;
int16_t adc2 = 0;
int16_t adc3 = 0;
float adc0V = 0.0000;
float adc1V = 0.0000;
float adc2V = 0.0000;
float adc3V = 0.0000;

float darkcurrent_limit = -10;


unsigned long integraltimemicros = 700;
int resettimemicros = 10;

bool printtoconsole = false;

unsigned int dccount = 30000;

unsigned int countvolt = 1;

unsigned long previousmillis = 0;
unsigned long initialintegralmicros = 0;
unsigned long integralmicros = 0;
unsigned long startmicros = 0;
unsigned long count = 0;

//to send current time to python
unsigned long timestartwatertank = 0;
unsigned long timeendwatertank = 0;


int potlow;
int pothigh;
int potnow = 0;


float setvolt = 41.93;
float PSV;

float temp = 27;
unsigned int tempbytes;

//to send voltages and temp
byte arraytosend[34];

//Not send voltages and temp
//byte arraytosend[24];


unsigned int chb[] = {0, 0, 0, 0, 0, 0, 0, 0};
float chv[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};


void setup() {

  
  
  //all pins output
  pinMode(CS_ADQ, OUTPUT);
  pinMode(RST, OUTPUT);
  pinMode(HOLD, OUTPUT);
  pinMode(SHD_PS, OUTPUT);
  pinMode(SHD_REF, OUTPUT);
  pinMode(CS_POT, OUTPUT);
  pinMode(TEST_PIN, OUTPUT);
  pinMode(C_RANGE, OUTPUT);
  pinMode(FAN_ON, OUTPUT);
  pinMode(CS_USB, OUTPUT);



  digitalWrite(CS_ADQ, HIGH);
  digitalWrite(RST, HIGH);
  digitalWrite(HOLD, LOW);
  digitalWrite(SHD_PS, LOW);
  digitalWrite(SHD_REF, LOW);
  digitalWrite(CS_POT, HIGH);
  digitalWrite(FAN_ON, LOW);
  digitalWrite(C_RANGE, LOW);
  digitalWrite(CS_USB, HIGH);

  Serial.begin(115200);
  Wire.begin();
  SPI.begin();

  //Dotstar
  led.begin();
  led.show(); //put dotstar off

  //Dotstar onboard to turn off
  led0.begin();
  led0.show(); //put onboard dotstar off

  fram.begin();


  //DAC AD5675R does not need initialization routine

  //Put all darkcurrents to -10 as default value
  setvoltDAC(0, 10000);
  setvoltDAC(1, 10000);
  setvoltDAC(2, 10000);
  setvoltDAC(3, 10000);
  setvoltDAC(4, 10000);
  setvoltDAC(5, 10000);
  setvoltDAC(6, 10000);
  setvoltDAC(7, 10000);


  tempsensor.begin(0x18); //this line on
  tempsensor.setResolution(3); //this line on
  // Mode Resolution SampleTime
  //  0    0.5°C       30 ms
  //  1    0.25°C      65 ms
  //  2    0.125°C     130 ms
  //  3    0.0625°C    250 ms
  tempsensor.wake(); //this line on

  Wire.setClock(400000);

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
  

  //Then wait 2 seconds and turn on the Power Suplly, ref and fan
  delay(2000);
  digitalWrite (SHD_PS, HIGH);
  digitalWrite(SHD_REF, HIGH);
  digitalWrite(FAN_ON, HIGH);
  

  //regulatePS(); //at the begining regulate PS
  //sdc(); //at the begining subtract dark current
  setpot(potnow);

  adc.setConvRate(ADS1115_860_SPS);
  adc.setVoltageRange_mV(ADS1115_RANGE_6144);

  
}


void loop() {
  

  if (micros() - initialintegralmicros >= integraltimemicros){
    ReadChannelsOnceandsend();
    
    //led turns blue to indicate it is integrating
    led.setPixelColor(0, colorblue);
    led.setBrightness(10);
    led.show();

    
    //digitalWrite(TEST_PIN, HIGH);
    //to calculate voltages and temp
    switch(countvolt){
      case 1:
        adc.setCompareChannels(ADS1115_COMP_0_GND);
        adc.startSingleMeasurement();
        led.setPixelColor(0, colorblue) ;
        led.setBrightness(10);
        led.show();
        break;
       case 6:
        adc0 = adc.getRawResult();
        arraytosend[10] = adc0 >> 8;
        arraytosend[11] = adc0 & 0xFF;
        //adc0V = adc.getResult_V();
        break;
       case 12:
        adc.setCompareChannels(ADS1115_COMP_1_GND);
        adc.startSingleMeasurement();
        break;
       case 18:
        adc1 = adc.getRawResult();
        arraytosend[12] = adc1 >> 8;
        arraytosend[13] = adc1 & 0xFF;
        //adc1V = adc.getResult_V();
        break;
       case 24:
        adc.setCompareChannels(ADS1115_COMP_2_GND);
        adc.startSingleMeasurement();
        break;
       case 30:
        adc2 = adc.getRawResult();
        arraytosend[14] = adc2 >> 8;
        arraytosend[15] = adc2 & 0xFF;
        //adc2V = adc.getResult_V();
        break;
       case 36:
        adc.setCompareChannels(ADS1115_COMP_3_GND);
        adc.startSingleMeasurement();
        break;
       case 42:
        adc3 = adc.getRawResult();
        arraytosend[16] = adc3 >> 8;
        arraytosend[17] = adc3 & 0xFF;
        //adc3V = adc.getResult_V();
        break;
       case 48:
        temp = tempsensor.readTempC();
        tempbytes = tempsensor.read16(0x05);
        arraytosend[8] = tempbytes >> 8;
        arraytosend[9] = tempbytes & 0xFF;
        break;
       case 54:
        countvolt = 0;
        break; 
    }
    countvolt += 1;
    //digitalWrite(TEST_PIN, LOW);
  }

  //PROTOCOLO DE COMUNICACION
  if (Serial.available() > 0) {
    char inChar = (char)Serial.read();

    //Change Integration time
    if (inChar == 'i'){
      String inttimestring = Serial.readStringUntil(',');
      integraltimemicros = (unsigned long)inttimestring.toInt();
      if (integraltimemicros >= 300000){
        resettimemicros = 70;
      }
      else {
        resettimemicros = 10;
      }
      Serial.print("Integral time set to ");
      Serial.println(inttimestring);
      Serial.print("Reset time set to ");
      Serial.println(resettimemicros);
      delay (1000);
      
    }

    if (inChar == 'e'){
      Serial.println("This is model11");
      delay (1000);
    }
    
    //Read or write FRAM memory
    if (inChar == 'm'){
      char readwrite = (char)Serial.read();
      String addrs = Serial.readStringUntil(',');
      //char comma = Serial.read(); //discard comma at the end
      uint16_t addr = (uint16_t)addrs.toInt();
      if (readwrite == 'r') {
        uint8_t test = fram.read(addr);
        Serial.print("Memory address: ");
        Serial.print(addr);
        Serial.print(" value read: ");
        Serial.println(test);
      }
      else if (readwrite == 'a'){
        uint8_t value;
        for (uint16_t a = 0; a < 32768; a++) {
              value = fram.read(a);
              //Serial.print("memory position: ");
              //Serial.print(a);
              //Serial.print(" memory value: ");
              Serial.println(value);
              if (value == 222){break;}   
        }
      }
      else if (readwrite == 'w'){
        String values = Serial.readStringUntil(',');
        char comma = Serial.read(); //discard comma at the end
        uint8_t value = (uint8_t)values.toInt();
        fram.write(addr, value);
        Serial.print("Memory address: ");
        Serial.print(addr);
        Serial.print(" value wrote: ");
        Serial.println(value);
      }
      delay(1000);
    }

    //Read PS manually
    if (inChar == 'a'){
      if (adc.init()){
        adc.setConvRate(ADS1115_860_SPS);
        adc.setVoltageRange_mV(ADS1115_RANGE_6144);
        readPS();
      }
      else {
        PSV = 1.1;
      }
      Serial.print("PS0 now is: ");
      Serial.println(PSV);
      delay(1000);
    }
    
    //REGULATE POWER SUPPLY    
    if (inChar == 'r'){
      String PSs = Serial.readStringUntil(',');
      char comma = Serial.read(); //discard comma at the end
      Serial.println(PSs.toFloat(), 2);
      setvolt = PSs.toFloat();
      regulatePS();
    }

    //SELECT INTEGRATOR CAPACITOR RANGE
    //expected value is cl (capacitor low) or ch (capacitor high)
    if (inChar == 'c'){
      char lh = (char)Serial.read();
      if (lh == 'l'){
        darkcurrent_limit = -10;
        digitalWrite(C_RANGE, LOW);
      }
      else{
        darkcurrent_limit = -10;
        digitalWrite(C_RANGE, HIGH);
      }
      
    }

    //READ INTEGRATOR CAPACITOR RANGE
    if (inChar == 'f'){
      int valcapacitor = 0;
      valcapacitor = digitalRead(C_RANGE);
      Serial.print("Capacitor selected: ");
      Serial.println(valcapacitor);
      delay(500);
    }
    

    //PRINT TO CONSOLE
    if (inChar == 'h'){
      printtoconsole = true;
    }

    if (inChar == 'b'){
      printtoconsole = false;
    }

    //SUBTRACT DARK CURRENT
    if (inChar == 's'){
     Serial.println("s preseed");
     delay(1000);
     sdc();
    }

    //RESTART MICROSECONDS CLOCK
    if (inChar == 't'){
      startmicros = micros();
      count = 0;
    }

    //Measure time start water tank
    if (inChar == '1'){
      timestartwatertank = micros() - startmicros;
    }

    //Measure time end water tank
    if (inChar == '2'){
      timeendwatertank = micros() - startmicros;
    }

    //Send time start and time end water tank to python
    if (inChar == '3'){
      delay(2000);
      Serial.print("Time Water Tank: ");
      Serial.print(timestartwatertank);
      Serial.print(",");
      Serial.println(timeendwatertank);
      delay(2000);
    }

    //SET DARK CURRENT MANUALLY
    if (inChar == 'd'){
      String ch = Serial.readStringUntil(',');
      //char comma = Serial.read();
      String dcvalue = Serial.readStringUntil(',');
      char comma2 = Serial.read();
      //for DAC ADS5675R
      //dcvalue can go from 0 to 65535
      setvoltDAC(ch.toInt(), dcvalue.toInt());
      Serial.print("Dark Current of ch ");
      Serial.print(ch);
      Serial.print(" set to ");
      Serial.println(dcvalue);
      delay(1000);
    }

    //SET THE POT MANUALLY
    //pot value in counts from 0 to 1023
    if (inChar == 'q'){
      String potvalue = Serial.readStringUntil(',');
      char comma = Serial.read();
      setpot(potvalue.toInt());
      Serial.print("Pot at ");
      Serial.println(potvalue);
    }

     //TURN ON OFF POWER SUPPLY
     if (inChar == 'w'){
      char ps = (char)Serial.read();
      if (ps == '1'){
        //Activate Power Supply
        Serial.println("PS ON");
        digitalWrite (SHD_PS, HIGH);
       }
      if (ps == '0'){
        //Dectivate Power Supply
        Serial.println("PS OFF");
        digitalWrite (SHD_PS, LOW);
      }
    }
  }
}


void ReadChannels() {
  //digitalWrite(TEST_PIN, HIGH);
  SPI.beginTransaction(SPISettings(17000000, MSBFIRST, SPI_MODE1));
  //initiate ch0 manual transfer
  //and read previous set ch7 from previous sample, discard
  digitalWrite(CS_ADQ, LOW);
  SPI.transfer16(0xC000);
  chb[7] = SPI.transfer16(0x0000);
  digitalWrite(CS_ADQ, HIGH);
  //initiate ch1 manual transfer
  //and read previous set ch0
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xC400);
  chb[0] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch2 manual transfer
  //and read previous set ch1
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xC800);
  chb[1] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch3 manual transfer
  //and read previous set ch2
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xCC00);
  chb[2] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch4 manual transfer
  //and read previous set ch3
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xD000);
  chb[3] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch5 manual transfer
  //and read previous set ch4
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xD400);
  chb[4] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch6 manual transfer
  //and read previous set ch5
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xD800);
  chb[5] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch7 manual transfer
  //and read previous set ch6
  digitalWrite (CS_ADQ, LOW);
  SPI.transfer16 (0xDC00);
  chb[6] = SPI.transfer16 (0x0000);
  digitalWrite (CS_ADQ, HIGH);
  //initiate ch0 manual transfer
  //and read previous set ch7
  //digitalWrite(CS_ADQ, LOW);
  //SPI.transfer16(0xC000);
  //chb[7] = SPI.transfer16(0x0000);
  //digitalWrite(CS_ADQ, HIGH);

  SPI.endTransaction();
  //digitalWrite(TEST_PIN, LOW);

  //NOt to send voltages and temp
  /*arraytosend[8] = chb[0] >> 8;
  arraytosend[9] = chb[0] & 0xFF;
  arraytosend[10] = chb[1] >> 8;
  arraytosend[11] = chb[1] & 0xFF;
  arraytosend[12] = chb[2] >> 8;
  arraytosend[13] = chb[2] & 0xFF;
  arraytosend[14] = chb[3] >> 8;
  arraytosend[15] = chb[3] & 0xFF;
  arraytosend[16] = chb[4] >> 8;
  arraytosend[17] = chb[4] & 0xFF;
  arraytosend[18] = chb[5] >> 8;
  arraytosend[19] = chb[5] & 0xFF;
  arraytosend[20] = chb[6] >> 8;
  arraytosend[21] = chb[6] & 0xFF;
  arraytosend[22] = chb[7] >> 8;
  arraytosend[23] = chb[7] & 0xFF;*/

  //Send voltages and temp
  arraytosend[18] = chb[0] >> 8;
  arraytosend[19] = chb[0] & 0xFF;
  arraytosend[20] = chb[1] >> 8;
  arraytosend[21] = chb[1] & 0xFF;
  arraytosend[22] = chb[2] >> 8;
  arraytosend[23] = chb[2] & 0xFF;
  arraytosend[24] = chb[3] >> 8;
  arraytosend[25] = chb[3] & 0xFF;
  arraytosend[26] = chb[4] >> 8;
  arraytosend[27] = chb[4] & 0xFF;
  arraytosend[28] = chb[5] >> 8;
  arraytosend[29] = chb[5] & 0xFF;
  arraytosend[30] = chb[6] >> 8;
  arraytosend[31] = chb[6] & 0xFF;
  arraytosend[32] = chb[7] >> 8;
  arraytosend[33] = chb[7] & 0xFF;
  

  chv[0] = -((float)chb[0] * 24/65535) + 12;
  chv[1] = -((float)chb[1] * 24/65535) + 12;
  chv[2] = -((float)chb[2] * 24/65535) + 12;
  chv[3] = -((float)chb[3] * 24/65535) + 12;
  chv[4] = -((float)chb[4] * 24/65535) + 12;
  chv[5] = -((float)chb[5] * 24/65535) + 12;
  chv[6] = -((float)chb[6] * 24/65535) + 12;
  chv[7] = -((float)chb[7] * 24/65535) + 12;
  //digitalWrite(TEST_PIN, LOW);
  
}

void ReadChannelsOnceandsend(){
   //digitalWrite(TEST_PIN, HIGH);
   ReadChannelsOnce();

    //digitalWrite(testpin, HIGH);
    arraytosend[0] = (count >> 24) & 0xFF;
    arraytosend[1] = (count >> 16) & 0xFF;
    arraytosend[2] = (count >> 8) & 0xFF;
    arraytosend[3] = count & 0xFF;

    unsigned long timesincestart = micros() - startmicros;
    arraytosend[4] = (timesincestart >> 24) & (0xFF);
    arraytosend[5] = (timesincestart >> 16) & (0xFF);
    arraytosend[6] = (timesincestart >> 8) & (0xFF);
    arraytosend[7] = timesincestart & 0xFF;

    if (printtoconsole){
      Serial.print(count);
      Serial.print(",");
      Serial.print(timesincestart);
      Serial.print(",");
      Serial.print(temp, 4);
      Serial.print(",");
      
      
      //adc0 PS0
      Serial.print(adc0*0.1875/1000*PSFC+PSFCind, 4);
      Serial.print(",");
      //adc1 -15V
      Serial.print(adc1*0.1875*-3.2353/1000, 4);
      Serial.print(",");
      //adc2 15V
      Serial.print(adc2*0.1875*4.2353/1000, 4);
      Serial.print(",");   
      //adc3 5V
      Serial.print(adc3*0.1875/1000, 4);
      
      Serial.print(",");
      Serial.print(chv[0], 4);
      Serial.print(",");
      Serial.print(chv[1], 4);
      Serial.print(",");
      Serial.print(chv[2], 4);
      Serial.print(",");
      Serial.print(chv[3], 4);
      Serial.print(",");
      Serial.print(chv[4], 4);
      Serial.print(",");
      Serial.print(chv[5], 4);
      Serial.print(",");
      Serial.print(chv[6], 4);
      Serial.print(",");
      Serial.println(chv[7], 4);
    }
    else{
      //Not send voltages and temp
      //Serial.write(arraytosend, 24);

      //send voltages and temp
      Serial.write(arraytosend, 34);
    }

    count = count + 1;
    //digitalWrite(TEST_PIN, LOW);
    
}

void ReadChannelsOnce() {
  
  //digitalWrite(TEST_PIN, HIGH);
  //hold starts
  digitalWrite(HOLD, HIGH);
  delayMicroseconds(10);
  ReadChannels();
  //digitalWrite (testpin, LOW);
  //reset the integration and a new integration process starts
  digitalWrite (RST, LOW);
  delayMicroseconds (resettimemicros);
  digitalWrite (RST, HIGH);
  delayMicroseconds(10);
  //Hold ends
  //digitalWrite(testpin,HIGH);
  digitalWrite (HOLD, LOW);
  //digitalWrite(TEST_PIN,LOW);
  //digitalWrite (testpin, HIGH);
  initialintegralmicros = micros();
}


void regulatePS(){
  led.setPixelColor(0, colormagenta);
  led.setBrightness(10);
  led.show();
  potnow = 582;
  setpot(potnow);
  delay (300);
  readPS();

  while (!((PSV <= (setvolt + 0.015)) && (PSV >= (setvolt - 0.015)))){
    if (Serial.available() > 0) {
    char inChar = (char)Serial.read();
        if (inChar == 'n'){
          break;
        }
    }
    
    //voltage is too high
    if (PSV > (setvolt + 0.015)){
      potnow = potnow - 1;
    }
    //voltage is too low
    else if (PSV < (setvolt - 0.015)){
      potnow = potnow + 1;
    }
    setpot(potnow);
    delay(300);
    readPS();
    Serial.print("setvolt,");
    Serial.print(setvolt, 2);
    //Serial.print(",pothigh,");
    //Serial.print(pothigh);
    Serial.print(",potnow,");
    Serial.print(potnow);
    //Serial.print(",daclow,");
    //Serial.print(daclow);
    Serial.print(",PS,");
    Serial.println(PSV, 4);

  }
  //turn led off after regulating
  led.setPixelColor(0, coloroff);
  led.show();
}

void readPS(){

  adc.setCompareChannels(ADS1115_COMP_0_GND);
  adc.startSingleMeasurement();
  while(adc.isBusy()){};
  PSV = adc.getResult_V() * PSFC + PSFCind;
  
}

//Use this function
//to set one channel
//for DAC ADS5675R
//dcvch goes form 0, 65535
void setvoltDAC(int ch, unsigned int dcvch){
  Wire.beginTransmission(0xF);
  Wire.write(48 + ch);
  Wire.write(dcvch >> 8);
  Wire.write(dcvch & 0xFF);
  Wire.endTransmission();
}


// set pot to be used with MAX5498ETE wiper output
void setpot(int x) {
  SPI.beginTransaction(SPISettings(7000000, MSBFIRST, SPI_MODE0));
  //set the pot
  digitalWrite(CS_POT, LOW);
  SPI.transfer(0x1);
  SPI.transfer16(x << 6);
  digitalWrite(CS_POT, HIGH);
  SPI.endTransaction();
}


//function to substract dark current
void sdc(){
 unsigned int dccount = 3000;


  //turn led green during substract dark current
  led.setPixelColor(0, colorgreen);
  led.setBrightness(10);
  led.show();
  Serial.println("Subtract Dark Current initiated");
  delay(500);
 
 for (int i = 0; i < 8; i++){
  if (Serial.available() > 0) {
        char inChar = (char)Serial.read();
        if (inChar == 'n'){
          break;
        }
      }
  dccount = 6000;
  int steps = 200;
  setvoltDAC(i, dccount);
  for (int i = 0; i < steps; i++){
      while (micros() - initialintegralmicros < (integraltimemicros)){}
      ReadChannelsOnce();
    }
  Serial.print(i);
  Serial.print(",");
  Serial.print(dccount);
  Serial.print(",");
  Serial.println(chv[i], 4);
  for (int k = 0; k < steps; k++){
    
    while (micros() - initialintegralmicros < (integraltimemicros)){}
    ReadChannelsOnce();
    }
  
  while (chv[i] > darkcurrent_limit){
    if (Serial.available() > 0) {
      char inChar = (char)Serial.read();
      if (inChar == 'n'){
        break;
      }
    }
   dccount = dccount + 250;
   setvoltDAC(i, dccount);
 for (int k = 0; k < steps; k++){
    
    while (micros() - initialintegralmicros < (integraltimemicros)){}
    ReadChannelsOnce();
    }
   

   Serial.print(i);
   Serial.print(",");
   Serial.print(dccount);
   Serial.print(",");
   Serial.println(chv[i], 4);
  }
 }
 Serial.println("finished");
 delay(1000);
 //turn led off after darkcurrent
 led.setPixelColor(0, coloroff);
 led.show();
}
