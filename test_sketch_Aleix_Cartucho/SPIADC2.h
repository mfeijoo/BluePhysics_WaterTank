#pragma once

#include <Arduino.h>
#include <SPI.h>

// Semplice driver per ADS8688A in modalità MAN_Ch_n, range massimo bipolare ±2.5*Vref
// Pensato per: Vref interno = 4.096 V, quindi FSR = ±10.24 V

class SpiAdc
{
public:
    // vref_volts: 4.096f se usi il riferimento interno
    // spiClockHz: tienilo basso (es. 1 MHz) per stare tranquillo
    SpiAdc(int csPin,
                  int sckPin,
                  int misoPin,
                  int mosiPin,
                  float vref_volts = 4.096f,
                  uint32_t spiClockHz = 16000000UL);

    void begin();

    // Letture RAW
    uint16_t readRaw(uint8_t channel, uint8_t samples = 1);
    inline uint16_t readRaw0(uint8_t samples = 1) { return readRaw(0, samples); }
    inline uint16_t readRaw1(uint8_t samples = 1) { return readRaw(1, samples); }

    // Conversione codice → tensione (bipolare, ±2.5*Vref)
    float codeToVolt(uint16_t code) const;

private:
    int      _csPin;
    int      _sckPin;
    int      _misoPin;
    int      _mosiPin;
    float    _vref;
    uint32_t _spiClockHz;

    uint8_t  _currentChannel;
    bool     _initialized;

    SPIClass* _spi;

    // Low-level
    void     writeProgramRegister(uint8_t addr, uint8_t data);
    uint16_t transferAndRead16(uint16_t cmd);

    uint16_t commandForChannel(uint8_t channel) const;
};
