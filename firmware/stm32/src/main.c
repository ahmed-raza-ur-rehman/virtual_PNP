#include "stm32_hal.h"
#include <stdio.h>
#include <string.h>

#define NUM_MOTORS 4
#define NUM_VACUUM 1
#define NUM_VISION 1

extern void motor_init(uint8_t, float);
extern void motor_enable(uint8_t);
extern void motor_update(uint8_t, float);
extern void vacuum_init(void);
extern void vision_init(void);
extern void encoder_init(uint8_t);
extern void adc_init_all(void);

volatile uint8_t system_state = 0;
volatile uint32_t tick_ms = 0;

void SysTick_Handler(void) {
    tick_ms++;
}

void system_init(void) {
    hal_init();
    hal_clock_init(168000000);
    // enable peripheral clocks
    RCC->AHB1ENR |= (1 << 0) | (1 << 1) | (1 << 2); // GPIOA,B,C
    RCC->APB1ENR |= (1 << 0) | (1 << 17); // TIM2, USART2
    RCC->APB2ENR |= (1 << 0) | (1 << 4) | (1 << 8); // TIM1, USART1, ADC1

    // init motors
    for (int i = 0; i < NUM_MOTORS; i++) {
        motor_init(i, 1000.0f);
    }
    // init vacuum
    vacuum_init();
    // init vision
    vision_init();
    // init encoders
    for (int i = 0; i < NUM_MOTORS; i++) {
        encoder_init(i);
    }
    // init ADC
    adc_init_all();
    // init watchdog
    hal_watchdog_init(5000);
}

void system_loop(void) {
    uint32_t last_tick = tick_ms;
    while (1) {
        if (tick_ms - last_tick >= 1) {
            last_tick = tick_ms;
            // update motors
            for (int i = 0; i < NUM_MOTORS; i++) {
                motor_update(i, 0.001f);
            }
            // update vacuum
            vacuum_update(1);
            // update encoders
            for (int i = 0; i < NUM_MOTORS; i++) {
                encoder_update(i, 1000);
            }
            // update ADC
            adc_update_all();
            // feed watchdog
            hal_watchdog_feed();
        }
    }
}

int main(void) {
    system_init();
    system_state = 1; // running
    system_loop();
    return 0;
}
