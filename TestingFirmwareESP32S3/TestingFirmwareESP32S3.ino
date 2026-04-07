#include "Adafruit_MCP9808.h"
#include <Adafruit_FRAM_I2C.h>
#include <Wire.h>

#define SDA_PIN     8
#define SCL_PIN     9

Adafruit_MCP9808 tempsensor = Adafruit_MCP9808();
Adafruit_FRAM_I2C fram = Adafruit_FRAM_I2C();

int counter = 0;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  delay(200);

  Wire.begin(SDA_PIN, SCL_PIN, 100000);


  tempsensor.begin(0x18);
  tempsensor.setResolution(3);
  tempsensor.wake();
  delay(200);
  float temp=tempsensor.readTempC();
  Serial.print("Temperature = ");
  Serial.print(temp);
  Serial.println(" C");

  bool x = fram.begin(MB85RC_DEFAULT_ADDRESS, &Wire);

  delay(500);

  uint16_t manufacturerID = 0, productID = 0;
  fram.getDeviceID(&manufacturerID, &productID);
  Serial.printf("FRAM Manufacturer ID: 0x%04X, 0x%04X, %d\n", manufacturerID, productID, x);
  
  delay(500);

}

void loop() {
  // put your main code here, to run repeatedly:
  float temp=tempsensor.readTempC();
  Serial.print("Temperature = ");
  Serial.print(temp);
  Serial.println(" C");
  delay(1000);
  uint8_t readData = 0;
  Serial.printf("fram state %d\n", fram.read(0, (uint8_t*)&readData, sizeof(readData))); 
  Serial.printf("fram data %d\n", readData);
  readData++;
  fram.write(0, &readData, sizeof(readData));

}
