#include "SPIADC2.h"

// Command words per MAN_Ch_n (tabella comandi ADS8688A)
// MAN_Ch_0 = 0xC000, MAN_Ch_1 = 0xC400, ecc.
static constexpr uint16_t CMD_MAN_CH0 = 0xC000;
static constexpr uint16_t CMD_MAN_CH1 = 0xC400;

SpiAdc::SpiAdc(int csPin,
                             int sckPin,
                             int misoPin,
                             int mosiPin,
                             float vref_volts,
                             uint32_t spiClockHz)
: _csPin(csPin),
  _sckPin(sckPin),
  _misoPin(misoPin),
  _mosiPin(mosiPin),
  _vref(vref_volts),
  _spiClockHz(spiClockHz),
  _currentChannel(0xFF),
  _initialized(false)
{
    _spi = &SPI;             // usa lo SPI di default dell’ESP32 (VSPI: 18/19/23)
}

void SpiAdc::begin()
{
    if (_initialized) return;

    pinMode(_csPin, OUTPUT);
    digitalWrite(_csPin, HIGH);

    // Inizializza SPI: MODE0, MSB first
    _spi->begin(_sckPin, _misoPin, _mosiPin, -1);

    // Non serve tenere una transaction aperta fissa, la apriamo ad ogni scambio

    // Configura range massimo bipolare per CH0 e CH1:
    // Range_CHn[3:0] = 0000 → ±2.5 * Vref (max range bipolare)
    writeProgramRegister(0x05, 0x00); // Channel 0 Input Range register
    writeProgramRegister(0x06, 0x00); // Channel 1 Input Range register

    _initialized = true;
}

// Scrittura registri di programma (ADDR[6:0], WR=1, data[7:0])
// Richiede ≥24 SCLK dopo CS falling edge
void SpiAdc::writeProgramRegister(uint8_t addr, uint8_t data)
{
    uint16_t cmd = (static_cast<uint16_t>(addr) << 9) | (1u << 8) | data;

    _spi->beginTransaction(SPISettings(_spiClockHz, MSBFIRST, SPI_MODE0));
    digitalWrite(_csPin, LOW);
    _spi->transfer16(cmd);     // primi 16 bit: indirizzo + WR + data
    _spi->transfer(0x00);      // altri 8 clock per rispettare i 24 SCLK minimi
    digitalWrite(_csPin, HIGH);
    _spi->endTransaction();
}

// Genera il comando MAN_Ch_n per il canale richiesto
uint16_t SpiAdc::commandForChannel(uint8_t channel) const
{
    switch (channel)
    {
        case 0: return CMD_MAN_CH0;
        case 1: return CMD_MAN_CH1;
        default:
            // Per ora supportiamo solo 0 e 1 in modo esplicito
            return CMD_MAN_CH0;
    }
}

// Esegue un frame completo (32 SCLK) e ritorna i 16 bit di conversione
//
// Il dispositivo:
//  - legge il comando sui primi 16 fronti di SCLK sulla SDI
//  - a partire dal 16° fronte, inizia a sparare su SDO i 16 bit di conversione (D15..D0)
// Qui facciamo due transfer16 consecutivi e ricomponiamo il valore:
//  - primo transfer16 legge 16 bit (bit0 = D15, bit15..1 = 0)
//  - secondo transfer16 legge i successivi 16 bit (bit15..1 = D14..D0, bit0 = 0)
//
// Quindi:
//   data = (word0_bit0 << 15) | (word1 >> 1);
uint16_t SpiAdc::transferAndRead16(uint16_t cmd)
{
    _spi->beginTransaction(SPISettings(_spiClockHz, MSBFIRST, SPI_MODE0));
    digitalWrite(_csPin, LOW);

    uint16_t w0 = _spi->transfer16(cmd);      // comandi + primi 16 bit SDO
    uint16_t w1 = _spi->transfer16(0x0000);   // altri 16 bit SDO

    digitalWrite(_csPin, HIGH);
    _spi->endTransaction();

    uint16_t d15 = (w0 & 0x0001u);           // bit0 del primo word = D15
    uint16_t rest = (w1 >> 1);               // bit15..1 del secondo word = D14..D0

    uint16_t code = static_cast<uint16_t>((d15 << 15) | rest);
    return code;
}

// Lettura RAW di un canale in modalità MAN_Ch_n
//
// Importante: il dato restituito in un frame è la conversione del canale selezionato
// nel frame precedente (pipeline di 1 frame).
//
// Strategia:
//  - se cambio canale → faccio un frame "di servizio" per selezionare il nuovo canale e butto il dato
//  - poi faccio un secondo frame sullo stesso canale e ritorno il valore di conversione valido


// ///valid stat

// uint16_t SpiAdc::readRaw(uint8_t channel, uint8_t samples)
// {
//     if (!_initialized) begin();

//     uint16_t cmd;
//     switch (channel)
//     {
//         case 0: cmd = CMD_MAN_CH0; break;
//         case 1: cmd = CMD_MAN_CH1; break;
//         default: cmd = CMD_MAN_CH0; break;
//     }

//     // 1) Se cambio canale, faccio un frame di servizio per selezionarlo
//     if (_currentChannel != channel) {
//         _spi->beginTransaction(SPISettings(_spiClockHz, MSBFIRST, SPI_MODE0));
//         digitalWrite(_csPin, LOW);
//         _spi->transfer16(cmd);      // 16 bit comando
//         _spi->transfer16(0x0000);   // 16 bit "vuoti"
//         digitalWrite(_csPin, HIGH);
//         _spi->endTransaction();

//         _currentChannel = channel;
//     }

//     // 2) Secondo frame: stesso comando, questa volta uso direttamente
//     // il secondo transfer16 come risultato (16 bit letti da SDO).
//     _spi->beginTransaction(SPISettings(_spiClockHz, MSBFIRST, SPI_MODE0));
//     digitalWrite(_csPin, LOW);
//     _spi->transfer16(cmd);        // comando (ignoro SDO)
//     uint16_t raw = _spi->transfer16(0x0000);   // qui leggo i 16 bit di output
//     digitalWrite(_csPin, HIGH);
//     _spi->endTransaction();

//     return raw;
// }

// ///valid end

uint16_t SpiAdc::readRaw(uint8_t channel, uint8_t samples)
{
    if (!_initialized) begin();
    if (samples == 0) return 0;

    uint16_t cmd;
    switch (channel)
    {
        case 0: cmd = CMD_MAN_CH0; break;
        case 1: cmd = CMD_MAN_CH1; break;
        default: cmd = CMD_MAN_CH0; break;
    }

    // 1) Se cambio canale, faccio un frame di servizio per selezionarlo
    if (_currentChannel != channel) {
        _spi->beginTransaction(SPISettings(_spiClockHz, MSBFIRST, SPI_MODE0));
        digitalWrite(_csPin, LOW);
        _spi->transfer16(cmd);      // 16 bit comando
        _spi->transfer16(0x0000);   // 16 bit "vuoti"
        digitalWrite(_csPin, HIGH);
        _spi->endTransaction();

        _currentChannel = channel;
    }

    uint32_t acc = 0;
    

    // 2) Secondo frame: stesso comando, questa volta uso direttamente
    // il secondo transfer16 come risultato (16 bit letti da SDO).
    _spi->beginTransaction(SPISettings(_spiClockHz, MSBFIRST, SPI_MODE0));
    digitalWrite(_csPin, LOW);

    for (uint8_t i = 0; i < samples; ++i) {
        // invio comando per questo frame
        _spi->transfer16(cmd);
        // leggo i 16 bit di output
        uint16_t raw = _spi->transfer16(0x0000);
        acc += raw;
    }

    digitalWrite(_csPin, HIGH);
    _spi->endTransaction();

    return static_cast<uint16_t>(acc / samples);
}


// uint16_t SpiAdc::readRaw(uint8_t channel)
// {
//     if (!_initialized) begin();

//     uint16_t cmd = commandForChannel(channel);

//     if (_currentChannel != channel)
//     {
//         // Primo frame per selezionare il canale (dato non valido)
//         (void)transferAndRead16(cmd);
//         _currentChannel = channel;
//     }

//     // Secondo frame: dato valido per il canale selezionato
//     uint16_t code = transferAndRead16(cmd);
//     return code;
// }




// Conversione codice → tensione, range bipolare ±2.5*Vref
//
// FSR = Vmax - Vmin = 5 * Vref (per ±2.5*Vref)
// Con codifica straight binary bipolare, usiamo la classica centratura su 0:
//   V = (code - 32768) * (FSR / 65536)
//
// Con Vref = 4.096 V → FSR = 20.48 V → ~312.5 µV/LSB
float SpiAdc::codeToVolt(uint16_t code) const
{
    const float fsr = 5.0f * _vref; // ±2.5*Vref → FSR totale
    float v = (static_cast<int32_t>(code) - 32768) * (fsr / 65536.0f);
    return v;
}
