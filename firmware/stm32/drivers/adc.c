#include "stm32_hal.h"

#define ADC_RESOLUTION 4095
#define NUM_ADC_CHANNELS 16

typedef struct {
    uint16_t raw[NUM_ADC_CHANNELS];
    float voltage[NUM_ADC_CHANNELS];
    float filtered[NUM_ADC_CHANNELS];
    float filter_alpha;
    uint8_t channel_enabled[NUM_ADC_CHANNELS];
    uint32_t sample_count;
} ADC_t;

static ADC_t adc;

void adc_init_all(void) {
    for (int i = 0; i < NUM_ADC_CHANNELS; i++) {
        adc.raw[i] = 0;
        adc.voltage[i] = 0.0f;
        adc.filtered[i] = 0.0f;
        adc.channel_enabled[i] = 0;
    }
    adc.filter_alpha = 0.2f;
    adc.sample_count = 0;
    hal_adc_init(ADC1, 0);
}

void adc_enable_channel(uint8_t ch) {
    if (ch >= NUM_ADC_CHANNELS) return;
    adc.channel_enabled[ch] = 1;
}

void adc_disable_channel(uint8_t ch) {
    if (ch >= NUM_ADC_CHANNELS) return;
    adc.channel_enabled[ch] = 0;
}

uint16_t adc_read_raw(uint8_t ch) {
    if (ch >= NUM_ADC_CHANNELS) return 0;
    adc.raw[ch] = hal_adc_read(ADC1, ch);
    return adc.raw[ch];
}

float adc_read_voltage(uint8_t ch, float vref) {
    if (ch >= NUM_ADC_CHANNELS) return 0.0f;
    uint16_t raw = adc_read_raw(ch);
    adc.voltage[ch] = (raw / (float)ADC_RESOLUTION) * vref;
    adc.filtered[ch] = adc.filter_alpha * adc.voltage[ch] + (1 - adc.filter_alpha) * adc.filtered[ch];
    return adc.filtered[ch];
}

float adc_read_temperature(void) {
    // internal temperature sensor
    uint16_t raw = adc_read_raw(16);
    float voltage = (raw / (float)ADC_RESOLUTION) * 3.3f;
    float temp = (voltage - 0.76f) / 0.0025f + 25.0f;
    return temp;
}

float adc_read_vref(void) {
    uint16_t raw = adc_read_raw(17);
    return (raw / (float)ADC_RESOLUTION) * 3.3f;
}

void adc_update_all(void) {
    for (int i = 0; i < NUM_ADC_CHANNELS; i++) {
        if (adc.channel_enabled[i]) {
            adc_read_voltage(i, 3.3f);
        }
    }
    adc.sample_count++;
}

uint16_t adc_get_raw(uint8_t ch) {
    if (ch >= NUM_ADC_CHANNELS) return 0;
    return adc.raw[ch];
}

float adc_get_filtered(uint8_t ch) {
    if (ch >= NUM_ADC_CHANNELS) return 0.0f;
    return adc.filtered[ch];
}
