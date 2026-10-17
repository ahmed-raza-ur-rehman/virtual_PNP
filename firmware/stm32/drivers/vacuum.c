#include "stm32_hal.h"

#define VACUUM_PUMP_PORT GPIOB
#define VACUUM_PUMP_PIN  0
#define VACUUM_VALVE_PORT GPIOB
#define VACUUM_VALVE_PIN  1
#define VACUUM_SENSOR_PORT GPIOB
#define VACUUM_SENSOR_PIN 2
#define VACUUM_TIMEOUT_MS 5000

typedef struct {
    uint8_t pump_on;
    uint8_t valve_open;
    float pressure;
    float target_pressure;
    uint8_t holding;
    uint32_t pickup_time;
    uint8_t fault;
    float min_pressure;
    float max_pressure;
} Vacuum_t;

static Vacuum_t vacuum;

void vacuum_init(void) {
    vacuum.pump_on = 0;
    vacuum.valve_open = 0;
    vacuum.pressure = 0.0f;
    vacuum.target_pressure = -80.0f; // kPa
    vacuum.holding = 0;
    vacuum.pickup_time = 0;
    vacuum.fault = 0;
    vacuum.min_pressure = -90.0f;
    vacuum.max_pressure = 0.0f;
    hal_gpio_init(VACUUM_PUMP_PORT, VACUUM_PUMP_PIN, GPIO_MODE_OUTPUT, GPIO_SPEED_LOW, GPIO_PULL_NONE, 0);
    hal_gpio_init(VACUUM_VALVE_PORT, VACUUM_VALVE_PIN, GPIO_MODE_OUTPUT, GPIO_SPEED_LOW, GPIO_PULL_NONE, 0);
    hal_gpio_init(VACUUM_SENSOR_PORT, VACUUM_SENSOR_PIN, GPIO_MODE_INPUT, GPIO_SPEED_LOW, GPIO_PULL_UP, 0);
}

void vacuum_pump_on(void) {
    vacuum.pump_on = 1;
    hal_gpio_write(VACUUM_PUMP_PORT, VACUUM_PUMP_PIN, 1);
}

void vacuum_pump_off(void) {
    vacuum.pump_on = 0;
    hal_gpio_write(VACUUM_PUMP_PORT, VACUUM_PUMP_PIN, 0);
}

void vacuum_valve_open(void) {
    vacuum.valve_open = 1;
    hal_gpio_write(VACUUM_VALVE_PORT, VACUUM_VALVE_PIN, 1);
}

void vacuum_valve_close(void) {
    vacuum.valve_open = 0;
    hal_gpio_write(VACUUM_VALVE_PORT, VACUUM_VALVE_PIN, 0);
}

float vacuum_read_pressure(void) {
    // read ADC
    uint16_t adc = hal_adc_read(ADC1, 0);
    vacuum.pressure = (adc / 4095.0f) * 100.0f - 100.0f; // map to -100..0 kPa
    return vacuum.pressure;
}

uint8_t vacuum_pickup(void) {
    vacuum_pump_on();
    vacuum_valve_close();
    uint32_t start = hal_get_tick();
    while (vacuum_read_pressure() > vacuum.target_pressure) {
        if (hal_get_tick() - start > VACUUM_TIMEOUT_MS) {
            vacuum.fault = 1;
            vacuum_pump_off();
            return 0;
        }
        hal_delay_ms(10);
    }
    vacuum.holding = 1;
    vacuum.pickup_time = hal_get_tick();
    return 1;
}

void vacuum_release(void) {
    vacuum_valve_open();
    hal_delay_ms(50);
    vacuum_pump_off();
    vacuum.holding = 0;
}

uint8_t vacuum_is_holding(void) {
    return vacuum.holding;
}

uint8_t vacuum_check_leak(void) {
    if (!vacuum.holding) return 0;
    float p = vacuum_read_pressure();
    if (p > vacuum.target_pressure + 10.0f) {
        // leak detected
        vacuum.fault = 1;
        return 1;
    }
    return 0;
}

void vacuum_update(uint32_t dt_ms) {
    vacuum_read_pressure();
    if (vacuum.holding) {
        vacuum_check_leak();
    }
}

uint8_t vacuum_has_fault(void) {
    return vacuum.fault;
}

void vacuum_clear_fault(void) {
    vacuum.fault = 0;
}

void vacuum_emergency_stop(void) {
    vacuum_pump_off();
    vacuum_valve_open();
    vacuum.holding = 0;
    vacuum.fault = 1;
}
